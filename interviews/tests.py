from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Profile
from apply.models import Application
from jobposts.models import JobPost

from .models import InterviewFeedback, InterviewSkillEndorsement, InterviewSlot


class InterviewFeedbackWorkflowTests(TestCase):
    def setUp(self):
        self.employer = User.objects.create_user(username="employer_feedback", password="pass12345")
        Profile.objects.create(user=self.employer, account_type=Profile.AccountType.EMPLOYER)

        self.other_employer = User.objects.create_user(username="other_employer", password="pass12345")
        Profile.objects.create(user=self.other_employer, account_type=Profile.AccountType.EMPLOYER)

        self.applicant = User.objects.create_user(username="applicant_feedback", password="pass12345")
        Profile.objects.create(
            user=self.applicant,
            account_type=Profile.AccountType.APPLICANT,
            skills="Python, Django, SQL",
        )

        self.job = JobPost.objects.create(
            owner=self.employer,
            title="Backend Engineer",
            company="Acme Inc",
            location="Atlanta, GA",
            pay_range="$100k-$130k",
            work_setting="hybrid",
            description="Build APIs",
        )
        self.application = Application.objects.create(
            user=self.applicant,
            job=self.job,
            resume_type="profile",
        )
        self.slot = InterviewSlot.create_from_duration(
            application=self.application,
            start_at=timezone.now() - timedelta(days=2),
            duration_minutes=60,
        )
        self.slot.status = InterviewSlot.Status.BOOKED
        self.slot.booked_at = timezone.now()
        self.slot.booked_by = self.applicant
        self.slot.save(update_fields=["status", "booked_at", "booked_by"])

        self.future_slot = InterviewSlot.create_from_duration(
            application=self.application,
            start_at=timezone.now() + timedelta(days=1),
            duration_minutes=60,
        )
        self.future_slot.status = InterviewSlot.Status.BOOKED
        self.future_slot.booked_at = timezone.now()
        self.future_slot.booked_by = self.applicant
        self.future_slot.save(update_fields=["status", "booked_at", "booked_by"])

    def _payload(
        self,
        recommendation="advance",
        rationale="Strong systems thinking and ownership.",
        slot=None,
        endorsed_skills=None,
    ):
        active_slot = slot or self.slot
        payload = {
            f"feedback-{active_slot.id}-technical_score": "4",
            f"feedback-{active_slot.id}-communication_score": "5",
            f"feedback-{active_slot.id}-problem_solving_score": "4",
            f"feedback-{active_slot.id}-recommendation": recommendation,
            f"feedback-{active_slot.id}-strengths": "Strong API design and collaboration.",
            f"feedback-{active_slot.id}-concerns": "Needs more depth in scaling experience.",
            f"feedback-{active_slot.id}-decision_rationale": rationale,
        }
        if endorsed_skills is not None:
            payload["endorsed_skills"] = endorsed_skills
        return payload

    def test_employer_can_save_structured_feedback(self):
        self.client.login(username="employer_feedback", password="pass12345")

        response = self.client.post(
            reverse("interviews:save_feedback", args=[self.slot.id]),
            data=self._payload(),
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("tab=emp-interviews", response.url)
        feedback = InterviewFeedback.objects.get(interview_slot=self.slot)
        self.assertEqual(feedback.employer, self.employer)
        self.assertEqual(feedback.recommendation, "advance")
        self.assertEqual(feedback.technical_score, 4)
        self.assertEqual(feedback.communication_score, 5)
        self.assertEqual(feedback.problem_solving_score, 4)
        self.assertEqual(feedback.decision_rationale, "Strong systems thinking and ownership.")

    def test_employer_can_update_existing_feedback(self):
        InterviewFeedback.objects.create(
            interview_slot=self.slot,
            employer=self.employer,
            technical_score=2,
            communication_score=2,
            problem_solving_score=2,
            recommendation="hold",
            strengths="",
            concerns="Needs follow-up interview.",
            decision_rationale="Need more data.",
        )
        self.client.login(username="employer_feedback", password="pass12345")

        response = self.client.post(
            reverse("interviews:save_feedback", args=[self.slot.id]),
            data=self._payload(recommendation="advance", rationale="Improved confidence after debrief."),
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(InterviewFeedback.objects.filter(interview_slot=self.slot).count(), 1)
        feedback = InterviewFeedback.objects.get(interview_slot=self.slot)
        self.assertEqual(feedback.recommendation, "advance")
        self.assertEqual(feedback.decision_rationale, "Improved confidence after debrief.")

    def test_employer_can_endorse_skills_from_feedback_modal(self):
        self.client.login(username="employer_feedback", password="pass12345")

        response = self.client.post(
            reverse("interviews:save_feedback", args=[self.slot.id]),
            data=self._payload(endorsed_skills=["Python", "Django"]),
        )

        self.assertEqual(response.status_code, 302)
        endorsed = set(
            InterviewSkillEndorsement.objects.filter(interview_slot=self.slot).values_list("skill_name", flat=True)
        )
        self.assertEqual(endorsed, {"Python", "Django"})

    def test_endorsements_are_replaced_on_feedback_update(self):
        InterviewSkillEndorsement.objects.create(
            interview_slot=self.slot,
            employer=self.employer,
            applicant=self.applicant,
            skill_name="Python",
        )
        self.client.login(username="employer_feedback", password="pass12345")

        response = self.client.post(
            reverse("interviews:save_feedback", args=[self.slot.id]),
            data=self._payload(endorsed_skills=["SQL"]),
        )

        self.assertEqual(response.status_code, 302)
        endorsed = list(
            InterviewSkillEndorsement.objects.filter(interview_slot=self.slot).values_list("skill_name", flat=True)
        )
        self.assertEqual(endorsed, ["SQL"])

    def test_other_employer_cannot_save_feedback(self):
        self.client.login(username="other_employer", password="pass12345")

        response = self.client.post(
            reverse("interviews:save_feedback", args=[self.slot.id]),
            data=self._payload(),
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(InterviewFeedback.objects.filter(interview_slot=self.slot).exists())

    def test_applicant_cannot_save_feedback(self):
        self.client.login(username="applicant_feedback", password="pass12345")

        response = self.client.post(
            reverse("interviews:save_feedback", args=[self.slot.id]),
            data=self._payload(),
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(InterviewFeedback.objects.filter(interview_slot=self.slot).exists())

    def test_employer_dashboard_shows_internal_feedback_section(self):
        self.client.login(username="employer_feedback", password="pass12345")

        response = self.client.get(reverse("jobposts.dashboard"), {"tab": "emp-interviews"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Internal Interview Feedback")
        self.assertContains(response, "Upcoming Scheduled Interviews")
        self.assertContains(response, "Past Interviews")
        self.assertContains(response, f'interviewFeedbackModal{self.slot.id}')
        self.assertNotContains(response, f'interviewFeedbackModal{self.future_slot.id}')

    def test_employer_cannot_save_feedback_before_interview_ends(self):
        self.client.login(username="employer_feedback", password="pass12345")

        response = self.client.post(
            reverse("interviews:save_feedback", args=[self.future_slot.id]),
            data=self._payload(slot=self.future_slot),
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(InterviewFeedback.objects.filter(interview_slot=self.future_slot).exists())

    def test_applicant_can_view_feedback_for_past_interview_when_available(self):
        InterviewFeedback.objects.create(
            interview_slot=self.slot,
            employer=self.employer,
            technical_score=4,
            communication_score=5,
            problem_solving_score=4,
            recommendation="advance",
            strengths="Great collaboration.",
            concerns="Could deepen system design examples.",
            decision_rationale="Strong fit for next round.",
        )
        self.client.login(username="applicant_feedback", password="pass12345")

        response = self.client.get(reverse("apply:application_status"), {"tab": "tab-interviews"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Past Interviews")
        self.assertContains(response, "View Feedback")
        self.assertContains(response, f"applicantFeedbackModal{self.slot.id}")

    def test_applicant_skill_badges_show_endorsement_company_tooltip(self):
        InterviewSkillEndorsement.objects.create(
            interview_slot=self.slot,
            employer=self.employer,
            applicant=self.applicant,
            skill_name="Python",
        )
        self.client.login(username="applicant_feedback", password="pass12345")

        response = self.client.get(reverse("apply:application_status"), {"tab": "tab-profile"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "title=\"Endorsed by Acme Inc\"")
        self.assertContains(response, "skill-indicator is-endorsed")

    def test_applicant_does_not_see_feedback_modal_when_no_feedback_exists(self):
        self.client.login(username="applicant_feedback", password="pass12345")

        response = self.client.get(reverse("apply:application_status"), {"tab": "tab-interviews"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No feedback shared yet.")
        self.assertNotContains(response, f"applicantFeedbackModal{self.slot.id}")

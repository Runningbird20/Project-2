#!/usr/bin/env python
import argparse
import os
import random
import sys
import uuid
from datetime import timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project2.settings")

import django  # noqa: E402

django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from django.db import transaction  # noqa: E402
from django.utils import timezone  # noqa: E402

from accounts.models import Profile  # noqa: E402
from apply.models import Application  # noqa: E402
from interviews.models import InterviewFeedback, InterviewSkillEndorsement, InterviewSlot  # noqa: E402
from jobposts.models import JobPost  # noqa: E402
from map.models import OfficeLocation  # noqa: E402


SKILLS = [
    "Python", "Django", "Flask", "FastAPI", "Java", "Spring", "C#", ".NET",
    "JavaScript", "TypeScript", "React", "Vue", "Angular", "Node.js",
    "SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis", "GraphQL", "REST",
    "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Terraform", "Linux",
    "Git", "CI/CD", "Testing", "PyTest", "Machine Learning", "Pandas",
]

JOB_TITLES = [
    "Software Engineer", "Backend Engineer", "Frontend Engineer",
    "Full Stack Engineer", "DevOps Engineer", "Data Engineer",
    "Machine Learning Engineer", "QA Engineer", "Site Reliability Engineer",
    "Platform Engineer", "Product Engineer",
]

COMPANY_NAMES = [
    "Northstar Labs", "BlueRiver Tech", "BrightForge", "Apex Orbit",
    "NovaPixel", "SummitWorks", "Cloud Harbor", "Vertex Systems",
    "SignalBridge", "Granite Digital",
]

COMPANY_PREFIXES = [
    "North", "South", "East", "West", "Summit", "Bright", "Blue", "Green", "Silver",
    "Golden", "Rapid", "Prime", "Quantum", "Nimbus", "Pioneer", "Urban", "Metro",
]

COMPANY_ROOTS = [
    "Harbor", "Bridge", "Labs", "Works", "Systems", "Digital", "Cloud", "Forge",
    "Motion", "Orbit", "Pixel", "Core", "Logic", "Scale", "Trail", "Pulse", "Matrix",
]

COMPANY_SUFFIXES = ["Inc", "Labs", "Tech", "Group", "Co", "Systems"]

STREET_NAMES = [
    "Peachtree", "Main", "Broad", "Pine", "Oak", "Maple", "Lake",
    "Cedar", "Willow", "Highland", "Park", "Washington", "Market",
    "Sunset", "Riverside", "Liberty", "Union", "King", "Madison",
    "Lakeview", "Magnolia", "Elm", "Monroe", "Jefferson", "Hill",
]

STREET_SUFFIXES = ["St", "Ave", "Blvd", "Rd", "Ln", "Way", "Dr"]

UNIT_LABELS = ["Suite", "Floor", "Unit"]

US_ZIP_INDEX = [
    ("30303", "Atlanta", "GA", 33.7490, -84.3880),
    ("30308", "Atlanta", "GA", 33.7715, -84.3856),
    ("78701", "Austin", "TX", 30.2672, -97.7431),
    ("78704", "Austin", "TX", 30.2465, -97.7602),
    ("98101", "Seattle", "WA", 47.6062, -122.3321),
    ("98104", "Seattle", "WA", 47.6026, -122.3282),
    ("80202", "Denver", "CO", 39.7392, -104.9903),
    ("60601", "Chicago", "IL", 41.8864, -87.6186),
    ("02108", "Boston", "MA", 42.3588, -71.0637),
    ("33101", "Miami", "FL", 25.7617, -80.1918),
    ("85004", "Phoenix", "AZ", 33.4510, -112.0685),
    ("94103", "San Francisco", "CA", 37.7725, -122.4091),
    ("10001", "New York", "NY", 40.7506, -73.9972),
    ("10018", "New York", "NY", 40.7547, -73.9925),
    ("90012", "Los Angeles", "CA", 34.0614, -118.2365),
    ("97204", "Portland", "OR", 45.5190, -122.6765),
    ("37203", "Nashville", "TN", 36.1522, -86.7896),
    ("27601", "Raleigh", "NC", 35.7796, -78.6382),
    ("55401", "Minneapolis", "MN", 44.9833, -93.2676),
    ("84101", "Salt Lake City", "UT", 40.7549, -111.8986),
    ("28202", "Charlotte", "NC", 35.2271, -80.8431),
    ("92101", "San Diego", "CA", 32.7157, -117.1611),
]

WORK_SETTINGS = ["remote", "onsite", "hybrid"]
COMPANY_SIZES = ["small", "mid_size", "large", "startup", "enterprise"]
APPLICATION_STATUS_WEIGHTS = [
    ("applied", 0.23),
    ("review", 0.24),
    ("interview", 0.27),
    ("offer", 0.14),
    ("rejected", 0.12),
]
EMPLOYER_RESPONSE_PROFILES = [
    # These ranges line up with SLA colors in the UI:
    # green < 49 hours, yellow <= 1 week, red > 1 week.
    {"name": "fast", "weight": 0.35, "min_hours": 6, "max_hours": 48},
    {"name": "standard", "weight": 0.45, "min_hours": 50, "max_hours": 160},
    {"name": "slow", "weight": 0.20, "min_hours": 170, "max_hours": 360},
]
INTERVIEW_DURATION_CHOICES = [30, 45, 60, 90]
INTERVIEW_NOTES = [
    "General technical interview.",
    "Focus on API design and system thinking.",
    "Behavioral + project deep dive.",
    "Team fit and communication assessment.",
]

COMPANY_BLURBS = [
    "builds software products used by teams around the world.",
    "ships cloud infrastructure for fast-growing businesses.",
    "creates AI-powered tools that improve developer productivity.",
    "helps enterprises modernize internal platforms and workflows.",
    "builds secure data products for regulated industries.",
    "develops customer-facing web platforms at scale.",
]

COMPANY_CULTURES = [
    "Ownership-minded team with strong mentorship and clear growth paths.",
    "Collaborative, low-ego culture with emphasis on quality and shipping fast.",
    "Remote-friendly culture focused on transparency and continuous learning.",
    "Product-driven engineering culture with weekly demos and customer feedback loops.",
    "Inclusive team environment with strong documentation and async collaboration.",
]

PERK_POOL = [
    "401(k) match",
    "Home office stipend",
    "Learning budget",
    "Flexible PTO",
    "Parental leave",
    "Commuter benefits",
    "Wellness stipend",
    "Health, dental, vision",
    "Annual team offsite",
    "Performance bonus",
]


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Populate PandaPulse with demo employers, applicants, job posts, applications, "
            "interviews, feedback, and skill endorsements."
        )
    )
    parser.add_argument("--employers", type=int, default=12, help="Number of employer accounts to create.")
    parser.add_argument("--applicants", type=int, default=30, help="Number of applicant accounts to create.")
    parser.add_argument("--jobs", type=int, default=70, help="Number of job posts to create.")
    parser.add_argument(
        "--applications-min-per-applicant",
        type=int,
        default=1,
        help="Minimum number of applications to create per applicant.",
    )
    parser.add_argument(
        "--applications-max-per-applicant",
        type=int,
        default=4,
        help="Maximum number of applications to create per applicant.",
    )
    parser.add_argument(
        "--interview-probability",
        type=float,
        default=0.70,
        help="Chance that an interview/offer/closed application gets seeded interviews.",
    )
    parser.add_argument(
        "--feedback-probability",
        type=float,
        default=0.75,
        help="Chance that a completed interview gets feedback.",
    )
    parser.add_argument(
        "--endorsement-probability",
        type=float,
        default=0.80,
        help="Chance that feedback includes endorsed skills.",
    )
    parser.add_argument("--password", default="Pass12345!", help="Password used for created users.")
    parser.add_argument("--prefix", default="seed", help="Username/email prefix for generated accounts.")
    parser.add_argument(
        "--clear-prefix",
        action="store_true",
        help="Delete previously generated users/job posts for this prefix before creating new data.",
    )
    parser.add_argument(
        "--clear-only",
        action="store_true",
        help="Delete previously generated users/job posts for this prefix and exit without creating new data.",
    )
    return parser.parse_args()


def pick_skills(min_count=3, max_count=7):
    count = random.randint(min_count, max_count)
    return ", ".join(sorted(random.sample(SKILLS, count)))


def random_address():
    zip_code, city, state, base_lat, base_lon = random.choice(US_ZIP_INDEX)
    line_1 = f"{random.randint(100, 9999)} {random.choice(STREET_NAMES)} {random.choice(STREET_SUFFIXES)}"
    line_2 = ""
    if random.random() < 0.45:
        line_2 = f"{random.choice(UNIT_LABELS)} {random.randint(2, 25)}{random.choice(['', 'A', 'B'])}"
    full = f"{line_1}, {city}, {state} {zip_code}, United States"
    if line_2:
        full = f"{line_1}, {line_2}, {city}, {state} {zip_code}, United States"
    latitude = round(base_lat + random.uniform(-0.09, 0.09), 6)
    longitude = round(base_lon + random.uniform(-0.09, 0.09), 6)
    return {
        "line_1": line_1,
        "line_2": line_2,
        "city": city,
        "state": state,
        "postal_code": zip_code,
        "country": "United States",
        "full": full,
        "latitude": latitude,
        "longitude": longitude,
    }


def random_company_name():
    if random.random() < 0.55:
        return random.choice(COMPANY_NAMES)
    return f"{random.choice(COMPANY_PREFIXES)} {random.choice(COMPANY_ROOTS)} {random.choice(COMPANY_SUFFIXES)}"


def random_company_website(company_name):
    compact = "".join(ch for ch in company_name.lower() if ch.isalnum())
    suffix = random.choice([".com", ".io", ".tech", ".co"])
    return f"https://www.{compact}{suffix}"


def random_company_perks():
    picks = random.sample(PERK_POOL, random.randint(3, 5))
    return "\n".join(picks)


def weighted_choice(weighted_items):
    roll = random.random()
    cumulative = 0.0
    for value, weight in weighted_items:
        cumulative += weight
        if roll <= cumulative:
            return value
    return weighted_items[-1][0]


def build_employer_response_profiles(employers):
    weighted_profiles = [
        (profile["name"], profile["weight"]) for profile in EMPLOYER_RESPONSE_PROFILES
    ]
    profile_map = {profile["name"]: profile for profile in EMPLOYER_RESPONSE_PROFILES}
    assignments = {}
    for employer in employers:
        profile_name = weighted_choice(weighted_profiles)
        profile_data = profile_map[profile_name]
        assignments[employer.id] = {
            "profile": profile_name,
            "baseline_hours": random.randint(profile_data["min_hours"], profile_data["max_hours"]),
            "min_hours": profile_data["min_hours"],
            "max_hours": profile_data["max_hours"],
        }
    return assignments


def random_response_delay_hours_for_employer(employer_id, response_profiles):
    assignment = response_profiles.get(employer_id)
    if not assignment:
        return random.randint(24, 120)

    # Keep each employer's response behavior clustered around a baseline.
    delay_hours = assignment["baseline_hours"] + random.randint(-12, 12)
    delay_hours = max(assignment["min_hours"], min(assignment["max_hours"], delay_hours))
    return delay_hours


def summarize_response_profiles(response_profiles):
    summary = {"fast": 0, "standard": 0, "slow": 0}
    for assignment in response_profiles.values():
        profile = assignment.get("profile")
        if profile in summary:
            summary[profile] += 1
    return summary


def parse_skill_csv(raw_value):
    seen = set()
    ordered = []
    for token in str(raw_value or "").replace(";", ",").split(","):
        skill = " ".join(token.split()).strip()
        if not skill:
            continue
        key = skill.lower()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(skill)
    return ordered


def random_meeting_link():
    return f"https://meet.pandapulse.demo/{uuid.uuid4().hex[:10]}"


def random_timestamp_between(start_dt, end_dt):
    if end_dt <= start_dt:
        return start_dt
    span_seconds = int((end_dt - start_dt).total_seconds())
    return start_dt + timedelta(seconds=random.randint(0, span_seconds))


def ensure_profile(user, account_type, **updates):
    profile, _ = Profile.objects.get_or_create(user=user)
    profile.account_type = account_type
    for key, value in updates.items():
        setattr(profile, key, value)
    profile.save()
    return profile


def create_employers(prefix, count, password):
    User = get_user_model()
    created = []
    index = 1
    while len(created) < count:
        username = f"{prefix}_emp_{index}"
        email = f"{username}@example.com"
        index += 1
        if User.objects.filter(username=username).exists():
            continue
        user = User.objects.create_user(username=username, email=email, password=password)
        company_name = random_company_name()
        address = random_address()
        ensure_profile(
            user,
            Profile.AccountType.EMPLOYER,
            company_name=company_name,
            company_website=random_company_website(company_name),
            company_description=f"{company_name} {random.choice(COMPANY_BLURBS)}",
            company_culture=random.choice(COMPANY_CULTURES),
            company_perks=random_company_perks(),
            location=address["full"],
            address_line_1=address["line_1"],
            address_line_2=address["line_2"],
            city=address["city"],
            state=address["state"],
            postal_code=address["postal_code"],
            country=address["country"],
            headline="",
            skills="",
            education="",
            work_experience="",
        )
        created.append(user)
    return created


def create_applicants(prefix, count, password):
    User = get_user_model()
    created = []
    index = 1
    while len(created) < count:
        username = f"{prefix}_app_{index}"
        email = f"{username}@example.com"
        index += 1
        if User.objects.filter(username=username).exists():
            continue
        user = User.objects.create_user(username=username, email=email, password=password)
        address = random_address()
        ensure_profile(
            user,
            Profile.AccountType.APPLICANT,
            headline=random.choice(
                [
                    "Backend-focused engineer",
                    "Full-stack builder",
                    "Cloud and platform specialist",
                    "Data-driven developer",
                ]
            ),
            skills=pick_skills(4, 9),
            education="BS in Computer Science",
            work_experience="2+ years building and shipping software products.",
            projects="Internal tools, APIs, and automation projects.",
            location=address["full"],
            address_line_1=address["line_1"],
            address_line_2=address["line_2"],
            city=address["city"],
            state=address["state"],
            postal_code=address["postal_code"],
            country=address["country"],
            company_name="",
            company_website="",
            company_description="",
            company_culture="",
            company_perks="",
            visible_to_recruiters=True,
        )
        created.append(user)
    return created


def create_jobs(prefix, employers, count):
    created = []
    if not employers:
        return created

    for _ in range(count):
        owner = random.choice(employers)
        owner_profile = getattr(owner, "profile", None)
        address = random_address()
        work_setting = random.choice(WORK_SETTINGS)
        title = random.choice(JOB_TITLES)
        min_salary = random.randint(80, 170) * 1000
        max_salary = min_salary + random.randint(15, 70) * 1000

        job = JobPost.objects.create(
            owner=owner,
            title=title,
            company=(owner_profile.company_name if owner_profile and owner_profile.company_name else random.choice(COMPANY_NAMES)),
            location=(
                "Remote, United States"
                if work_setting == "remote"
                else f"{address['city']}, {address['state']}"
            ),
            pay_range=f"${min_salary // 1000}k-${max_salary // 1000}k",
            skills=pick_skills(4, 10),
            salary_min=min_salary,
            salary_max=max_salary,
            work_setting=work_setting,
            company_size=random.choice(COMPANY_SIZES),
            visa_sponsorship=random.choice([True, False]),
            description=(
                f"We are looking for a {title} to help build and scale our products. "
                "You will collaborate with cross-functional teams and ship customer-facing features."
            ),
        )
        created.append(job)

        if work_setting != "remote":
            OfficeLocation.objects.update_or_create(
                job_post=job,
                defaults={
                    "address_line_1": address["line_1"],
                    "address_line_2": address["line_2"],
                    "city": address["city"],
                    "state": address["state"],
                    "postal_code": address["postal_code"],
                    "country": address["country"],
                    "latitude": address["latitude"],
                    "longitude": address["longitude"],
                },
            )
    return created


def create_applications(
    applicants,
    jobs,
    min_per_applicant=1,
    max_per_applicant=4,
    employer_response_profiles=None,
):
    created = []
    if not applicants or not jobs:
        return created

    now = timezone.now()
    min_count = max(0, min_per_applicant)
    max_count = max(min_count, max_per_applicant)

    for applicant in applicants:
        target = random.randint(min_count, max_count)
        target = min(target, len(jobs))
        if target <= 0:
            continue

        for job in random.sample(jobs, target):
            status = weighted_choice(APPLICATION_STATUS_WEIGHTS)
            application = Application.objects.create(
                user=applicant,
                job=job,
                note=f"Interested in {job.title} and relevant to {job.company}.",
                resume_type="profile",
                status=status,
            )

            responded_at = None
            if status != "applied":
                delay_hours = random_response_delay_hours_for_employer(
                    job.owner_id,
                    employer_response_profiles or {},
                )
                # Ensure the application existed long enough for this response delay.
                min_age_hours = min((120 * 24) - 1, delay_hours + random.randint(6, 36))
                age_hours = random.randint(max(8, min_age_hours), 120 * 24)
                applied_at = now - timedelta(
                    hours=age_hours,
                    minutes=random.randint(0, 59),
                )
                responded_at = applied_at + timedelta(
                    hours=delay_hours,
                    minutes=random.randint(0, 45),
                )
            else:
                applied_at = now - timedelta(
                    days=random.randint(2, 120),
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59),
                )

            updates = {"applied_at": applied_at}

            viewed = random.random() < (0.94 if status != "applied" else 0.55)
            updates["employer_viewed"] = viewed
            if viewed:
                viewed_end = responded_at if responded_at else now
                updates["employer_viewed_at"] = random_timestamp_between(applied_at, viewed_end)

            if responded_at:
                updates["responded_at"] = responded_at
                if status == "rejected":
                    updates["rejected_at"] = responded_at
                    updates["auto_rejected_for_timeout"] = False
                    updates["rejected_offer_by_applicant"] = False

            Application.objects.filter(id=application.id).update(**updates)
            application.refresh_from_db()
            created.append(application)
    return created


def _random_interview_start(now, past=False):
    if past:
        base = now - timedelta(days=random.randint(1, 45))
    else:
        base = now + timedelta(days=random.randint(1, 30))
    return base.replace(
        hour=random.randint(9, 17),
        minute=random.choice([0, 15, 30, 45]),
        second=0,
        microsecond=0,
    )


def create_interviews_feedback_and_endorsements(
    applications,
    interview_probability=0.70,
    feedback_probability=0.75,
    endorsement_probability=0.80,
):
    stats = {
        "interview_slots": 0,
        "booked_slots": 0,
        "open_slots": 0,
        "canceled_slots": 0,
        "feedback_entries": 0,
        "skill_endorsements": 0,
    }
    if not applications:
        return stats

    now = timezone.now()
    eligible = [app for app in applications if app.status in {"interview", "offer"}]
    booked_past_slots = []
    feedback_slots = []
    for application in eligible:
        if random.random() > interview_probability:
            continue

        if application.status == "offer":
            primary_kind = weighted_choice([("past_booked", 0.9), ("upcoming_booked", 0.1)])
        else:
            primary_kind = weighted_choice([("past_booked", 0.45), ("upcoming_booked", 0.4), ("open_future", 0.15)])

        primary_start = _random_interview_start(now, past=(primary_kind == "past_booked"))
        primary_duration = random.choice(INTERVIEW_DURATION_CHOICES)
        primary_slot = InterviewSlot.create_from_duration(
            application=application,
            start_at=primary_start,
            duration_minutes=primary_duration,
            meeting_link=random_meeting_link(),
            notes=random.choice(INTERVIEW_NOTES),
        )
        stats["interview_slots"] += 1

        if primary_kind in {"past_booked", "upcoming_booked"}:
            booked_at = primary_slot.start_at - timedelta(
                days=random.randint(0, 7),
                hours=random.randint(2, 20),
            )
            if booked_at > now:
                booked_at = now - timedelta(hours=random.randint(2, 48))
            primary_slot.status = InterviewSlot.Status.BOOKED
            primary_slot.booked_at = booked_at
            primary_slot.booked_by = application.user
            primary_slot.save(update_fields=["status", "booked_at", "booked_by"])
            stats["booked_slots"] += 1
            if primary_slot.end_at <= now:
                booked_past_slots.append(primary_slot)
        else:
            stats["open_slots"] += 1

        if (
            primary_slot.status == InterviewSlot.Status.BOOKED
            and primary_slot.end_at <= now
            and random.random() <= feedback_probability
        ):
            feedback = InterviewFeedback.objects.create(
                interview_slot=primary_slot,
                employer=application.job.owner,
                technical_score=random.randint(2, 5),
                communication_score=random.randint(2, 5),
                problem_solving_score=random.randint(2, 5),
                recommendation=weighted_choice(
                    [("advance", 0.6), ("hold", 0.25), ("reject", 0.15)]
                ),
                strengths=random.choice(
                    [
                        "Strong communication and collaboration.",
                        "Clear problem-solving approach with good tradeoff analysis.",
                        "Solid fundamentals and practical project experience.",
                        "Good ownership mindset and thoughtful questions.",
                    ]
                ),
                concerns=random.choice(
                    [
                        "Could provide deeper system design detail.",
                        "Needs more examples around scaling and reliability.",
                        "Would benefit from stronger test strategy articulation.",
                        "No major concerns noted.",
                    ]
                ),
                decision_rationale=random.choice(
                    [
                        "Performance aligned with role expectations and team needs.",
                        "Interview signals indicate a strong potential fit for the team.",
                        "Mixed interview signals suggest additional evaluation may help.",
                    ]
                ),
            )
            stats["feedback_entries"] += 1
            feedback_slots.append(primary_slot)

            if random.random() <= endorsement_probability:
                applicant_skills = parse_skill_csv(getattr(application.user.profile, "skills", ""))
                if applicant_skills:
                    endorsed_count = random.randint(1, min(4, len(applicant_skills)))
                    for skill in random.sample(applicant_skills, endorsed_count):
                        InterviewSkillEndorsement.objects.create(
                            interview_slot=primary_slot,
                            employer=application.job.owner,
                            applicant=application.user,
                            skill_name=skill,
                        )
                        stats["skill_endorsements"] += 1

        extra_slots = random.randint(0, 2)
        for _ in range(extra_slots):
            extra_slot = InterviewSlot.create_from_duration(
                application=application,
                start_at=_random_interview_start(now, past=False),
                duration_minutes=random.choice(INTERVIEW_DURATION_CHOICES),
                meeting_link=random_meeting_link(),
                notes=random.choice(INTERVIEW_NOTES),
            )
            stats["interview_slots"] += 1
            if random.random() < 0.35:
                extra_slot.status = InterviewSlot.Status.CANCELED
                extra_slot.save(update_fields=["status"])
                stats["canceled_slots"] += 1
            else:
                stats["open_slots"] += 1

    if not booked_past_slots and eligible:
        fallback_app = random.choice(eligible)
        fallback_slot = InterviewSlot.create_from_duration(
            application=fallback_app,
            start_at=_random_interview_start(now, past=True),
            duration_minutes=random.choice(INTERVIEW_DURATION_CHOICES),
            meeting_link=random_meeting_link(),
            notes=random.choice(INTERVIEW_NOTES),
        )
        fallback_slot.status = InterviewSlot.Status.BOOKED
        fallback_slot.booked_at = fallback_slot.start_at - timedelta(days=2)
        fallback_slot.booked_by = fallback_app.user
        fallback_slot.save(update_fields=["status", "booked_at", "booked_by"])
        booked_past_slots.append(fallback_slot)
        stats["interview_slots"] += 1
        stats["booked_slots"] += 1

    if booked_past_slots and stats["feedback_entries"] == 0:
        fallback_slot = random.choice(booked_past_slots)
        InterviewFeedback.objects.create(
            interview_slot=fallback_slot,
            employer=fallback_slot.employer,
            technical_score=4,
            communication_score=4,
            problem_solving_score=4,
            recommendation="advance",
            strengths="Consistent interview performance.",
            concerns="No major concerns noted.",
            decision_rationale="Strong fit based on interview discussion and project examples.",
        )
        feedback_slots.append(fallback_slot)
        stats["feedback_entries"] += 1

    if feedback_slots and stats["skill_endorsements"] == 0:
        fallback_slot = random.choice(feedback_slots)
        fallback_skills = parse_skill_csv(getattr(fallback_slot.applicant.profile, "skills", ""))
        if fallback_skills:
            InterviewSkillEndorsement.objects.create(
                interview_slot=fallback_slot,
                employer=fallback_slot.employer,
                applicant=fallback_slot.applicant,
                skill_name=random.choice(fallback_skills),
            )
            stats["skill_endorsements"] += 1

    return stats


def clear_seed_data(prefix):
    User = get_user_model()
    users = User.objects.filter(username__startswith=f"{prefix}_")
    user_ids = list(users.values_list("id", flat=True))

    # Remove jobs owned by seeded users first (cascades office locations).
    deleted_jobs, _ = JobPost.objects.filter(owner_id__in=user_ids).delete()
    deleted_users, _ = users.delete()
    return deleted_users, deleted_jobs


def main():
    args = parse_args()
    random.seed()

    with transaction.atomic():
        if args.clear_prefix or args.clear_only:
            deleted_users, deleted_jobs = clear_seed_data(args.prefix)
            print(f"Deleted users: {deleted_users}")
            print(f"Deleted jobs/related rows: {deleted_jobs}")
            if args.clear_only:
                print(f"Cleanup complete for prefix: {args.prefix}_*")
                return

        employers = create_employers(args.prefix, args.employers, args.password)
        applicants = create_applicants(args.prefix, args.applicants, args.password)
        jobs = create_jobs(args.prefix, employers, args.jobs)
        response_profiles = build_employer_response_profiles(employers)
        response_profile_summary = summarize_response_profiles(response_profiles)
        applications = create_applications(
            applicants,
            jobs,
            min_per_applicant=args.applications_min_per_applicant,
            max_per_applicant=args.applications_max_per_applicant,
            employer_response_profiles=response_profiles,
        )
        interview_stats = create_interviews_feedback_and_endorsements(
            applications,
            interview_probability=args.interview_probability,
            feedback_probability=args.feedback_probability,
            endorsement_probability=args.endorsement_probability,
        )

    print("Seed complete.")
    print(f"Created employers: {len(employers)}")
    print(f"Created applicants: {len(applicants)}")
    print(f"Created job posts: {len(jobs)}")
    print(f"Created applications: {len(applications)}")
    print(
        "Employer response profiles: "
        f"fast={response_profile_summary['fast']}, "
        f"standard={response_profile_summary['standard']}, "
        f"slow={response_profile_summary['slow']}"
    )
    print(f"Created interview slots: {interview_stats['interview_slots']}")
    print(f"Created booked interviews: {interview_stats['booked_slots']}")
    print(f"Created open interviews: {interview_stats['open_slots']}")
    print(f"Created canceled interviews: {interview_stats['canceled_slots']}")
    print(f"Created interview feedback entries: {interview_stats['feedback_entries']}")
    print(f"Created skill endorsements: {interview_stats['skill_endorsements']}")
    print(f"Username prefix: {args.prefix}_*")
    print(f"Password: {args.password}")


if __name__ == "__main__":
    main()

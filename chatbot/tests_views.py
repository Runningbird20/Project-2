from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import Profile


class DummyAuthError(Exception):
    status_code = 401


class PandaAssistantErrorHandlingTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="chatuser",
            password="StrongPass123!",
            email="chatuser@example.com",
        )
        Profile.objects.create(user=self.user, account_type=Profile.AccountType.APPLICANT)
        self.client.login(username="chatuser", password="StrongPass123!")

    @override_settings(OPENROUTER_API_KEY="test-openrouter-key")
    @patch("chatbot.views.get_comprehensive_site_context", return_value="Site context")
    @patch("chatbot.views.openai.OpenAI")
    def test_authentication_error_returns_friendly_openrouter_message(
        self,
        mock_openai_client,
        _mock_site_context,
    ):
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = DummyAuthError(
            "Error code: 401 - {'error': {'message': 'User not found.', 'code': 401}}"
        )
        mock_openai_client.return_value = mock_client

        response = self.client.post(reverse("chatbot:ask_panda"), {"message": "hello panda"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "could not authenticate with OpenRouter")
        self.assertContains(response, "OPENROUTER_API_KEY")
        self.assertNotContains(response, "User not found.")

from pathlib import Path

from django.conf import settings
from django.test import TestCase
from django.urls import reverse


class ChatbotWidgetTests(TestCase):
    def test_base_template_includes_thinking_indicator_assets(self):
        response = self.client.get(reverse("home.index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Panda is thinking")
        self.assertContains(response, "showThinkingIndicator")
        self.assertContains(response, "chatbot-thinking-dots")

    def test_panda_assets_default_to_bottom_left_with_session_positioning(self):
        css = (Path(settings.BASE_DIR) / "project2" / "static" / "mascot" / "panda.css").read_text(encoding="utf-8")
        js = (Path(settings.BASE_DIR) / "project2" / "static" / "mascot" / "panda.js").read_text(encoding="utf-8")

        self.assertIn("left: 18px;", css)
        self.assertIn("bottom: 18px;", css)
        self.assertIn("sessionStorage", js)
        self.assertIn("updateBubblePlacement", js)

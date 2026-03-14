from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from apply.resume_parser import extract_skills


class ResumeParserTests(TestCase):
    @override_settings(OPENAI_API_KEY="test-openai-key", OPENAI_RESUME_PARSER_MODEL="gpt-4.1-mini")
    @patch("apply.resume_parser.OpenAI")
    def test_extract_skills_uses_openai_structured_output_and_keeps_keyword_fallback(self, mock_openai):
        parsed_message = MagicMock(skills=["Python", "LangChain"])
        completion = MagicMock()
        completion.choices = [MagicMock(message=MagicMock(parsed=parsed_message))]
        client = MagicMock()
        client.chat.completions.parse.return_value = completion
        mock_openai.return_value = client

        skills = extract_skills("Built Python services with LangChain and Django.")

        self.assertEqual(skills, ["Python", "LangChain", "django"])
        client.chat.completions.parse.assert_called_once()

    @patch("apply.resume_parser.OpenAI")
    @override_settings(OPENAI_API_KEY="test-openai-key")
    def test_extract_skills_falls_back_when_openai_call_fails(self, mock_openai):
        client = MagicMock()
        client.chat.completions.parse.side_effect = RuntimeError("boom")
        mock_openai.return_value = client

        skills = extract_skills("Experienced Python and Django engineer.")

        self.assertEqual(skills, ["python", "django"])

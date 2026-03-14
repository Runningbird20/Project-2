import logging
import os
import re
import tempfile

from django.conf import settings
from openai import OpenAI
from pydantic import BaseModel, Field

from project2.skills import get_custom_skill_options

try:
    from pypdf import PdfReader
except ImportError:
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        PdfReader = None

SKILL_LIBRARY = {
    # Programming Languages
    "python": ["python", "python3", "python programming"],
    "javascript": ["javascript", "js", "nodejs", "node.js"],
    "typescript": ["typescript", "ts"],
    "java": ["java", "jvm"],
    "c++": ["c++", "cpp"],
    "c#": ["c#", "c sharp", "dotnet", ".net"],
    "go": ["go", "golang"],
    "ruby": ["ruby", "ruby on rails", "ror"],
    "php": ["php", "php7", "php8"],
    "swift": ["swift", "ios swift"],
    "kotlin": ["kotlin", "android kotlin"],
    "rust": ["rust", "rustlang"],

    # Web Frameworks
    "react": ["react", "react.js", "reactjs"],
    "vue": ["vue", "vue.js", "vuejs"],
    "angular": ["angular", "angular.js", "angularjs"],
    "svelte": ["svelte", "sveltekit"],
    "next.js": ["next.js", "nextjs"],
    "nuxt.js": ["nuxt.js", "nuxtjs"],
    "django": ["django", "django framework"],
    "flask": ["flask", "flask framework"],
    "fastapi": ["fastapi"],
    "express": ["express", "express.js", "expressjs"],
    "spring": ["spring", "spring boot"],

    # Databases
    "sql": ["sql"],
    "postgresql": ["postgresql", "postgres", "psql"],
    "mysql": ["mysql"],
    "sqlite": ["sqlite"],
    "mongodb": ["mongodb", "mongo"],
    "redis": ["redis"],
    "oracle": ["oracle db", "oracle database"],
    "dynamodb": ["dynamodb", "aws dynamodb"],
    "snowflake": ["snowflake"],

    # Cloud Platforms
    "aws": ["aws", "amazon web services"],
    "azure": ["azure", "microsoft azure"],
    "gcp": ["gcp", "google cloud", "google cloud platform"],
    "heroku": ["heroku"],
    "digitalocean": ["digitalocean", "do cloud"],

    # DevOps & CI/CD
    "docker": ["docker", "docker containers"],
    "kubernetes": ["kubernetes", "k8s"],
    "jenkins": ["jenkins"],
    "github actions": ["github actions", "gh actions"],
    "gitlab ci": ["gitlab ci", "gitlab pipelines"],
    "terraform": ["terraform", "iac terraform"],
    "ansible": ["ansible"],
    "ci/cd": ["ci/cd", "continuous integration", "continuous deployment"],

    # Data Science / ML
    "pandas": ["pandas"],
    "numpy": ["numpy"],
    "scikit-learn": ["scikit-learn", "sklearn"],
    "tensorflow": ["tensorflow", "tf"],
    "pytorch": ["pytorch", "torch"],
    "matplotlib": ["matplotlib"],
    "seaborn": ["seaborn"],
    "jupyter": ["jupyter", "jupyter notebook"],
    "mlflow": ["mlflow"],

    # Tools & Platforms
    "git": ["git", "version control"],
    "linux": ["linux", "unix"],
    "bash": ["bash", "shell scripting"],
    "jira": ["jira", "atlassian jira"],
    "confluence": ["confluence"],
    "figma": ["figma"],
    "postman": ["postman", "api testing"],
    "webpack": ["webpack"],
    "vite": ["vite"],

    # Mobile Development
    "android": ["android", "android development"],
    "ios": ["ios", "ios development"],
    "react native": ["react native"],
    "flutter": ["flutter", "dart flutter"],

    # Testing
    "jest": ["jest"],
    "mocha": ["mocha"],
    "pytest": ["pytest"],
    "selenium": ["selenium"],
    "cypress": ["cypress"],

    # Other Common Resume Skills
    "graphql": ["graphql"],
    "rest api": ["rest", "rest api", "restful services"],
    "microservices": ["microservices", "microservice architecture"],
    "agile": ["agile", "scrum"],
}

logger = logging.getLogger(__name__)
RESUME_TEXT_CHAR_LIMIT = 24000


class ResumeSkillExtraction(BaseModel):
    skills: list[str] = Field(default_factory=list)


def extract_text_from_pdf(file_path):
    if PdfReader is None:
        raise RuntimeError("Missing PDF parser dependency. Install 'pypdf'.")

    text = ""
    with open(file_path, "rb") as f:
        reader = PdfReader(f)
        for page in reader.pages:
            page_text = page.extract_text() or ""
            if page_text:
                text += page_text + "\n"
    return text


def _contains_skill_term(text, term):
    pattern = rf"(?<![A-Za-z0-9]){re.escape(term)}(?![A-Za-z0-9])"
    return re.search(pattern, text, re.IGNORECASE)

def _normalize_skill_values(raw_skills):
    normalized = []
    seen = set()
    for raw_skill in raw_skills or []:
        skill = " ".join(str(raw_skill or "").strip().split())
        if not skill:
            continue
        key = skill.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(skill)
    return normalized


def extract_skills_keyword_fallback(text):
    found = []
    seen = set()
    for canonical, variants in SKILL_LIBRARY.items():
        for v in variants:
            if _contains_skill_term(text, v):
                if canonical not in seen:
                    seen.add(canonical)
                    found.append(canonical)
                break
    for custom_skill in get_custom_skill_options():
        key = custom_skill.lower()
        if key in seen:
            continue
        if _contains_skill_term(text, custom_skill):
            seen.add(key)
            found.append(custom_skill)
    return found


def _extract_skills_with_openai(text):
    if not settings.OPENAI_API_KEY:
        return []

    truncated_text = (text or "").strip()[:RESUME_TEXT_CHAR_LIMIT]
    if not truncated_text:
        return []

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    completion = client.chat.completions.parse(
        model=settings.OPENAI_RESUME_PARSER_MODEL or "gpt-4.1-mini",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": (
                    "You extract resume skills for a recruiting product. "
                    "Return only concrete, resume-relevant skills explicitly supported by the text. "
                    "Include programming languages, frameworks, libraries, cloud platforms, tools, data technologies, "
                    "platforms, and clearly stated methodologies. "
                    "Exclude job titles, company names, degrees, certifications, soft skills, and vague responsibilities. "
                    "Use concise canonical names like Python, Django, AWS, LangChain, Node.js, C#, SQL."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Extract the skills from this resume text and return them in the schema.\n\n"
                    f"{truncated_text}"
                ),
            },
        ],
        response_format=ResumeSkillExtraction,
    )
    parsed_message = completion.choices[0].message.parsed
    if not parsed_message:
        return []
    return _normalize_skill_values(parsed_message.skills)


def extract_skills(text):
    keyword_skills = extract_skills_keyword_fallback(text)
    try:
        openai_skills = _extract_skills_with_openai(text)
    except Exception as exc:
        logger.warning("OpenAI resume skill extraction failed; falling back to local parser: %s", exc)
        openai_skills = []

    merged = []
    seen = set()
    for skill in openai_skills + keyword_skills:
        key = skill.lower()
        if key in seen:
            continue
        seen.add(key)
        merged.append(skill)
    return merged

def parse_resume(file_path):
    # Detect PDF by extension
    if file_path.lower().endswith(".pdf"):
        text = extract_text_from_pdf(file_path)
    else:
        # fallback for .txt
        with open(file_path, "r", errors="ignore") as f:
            text = f.read()

    skills = extract_skills(text)

    return {
        "skills": skills,
        "raw_text": text,
    }


def parse_uploaded_resume(uploaded_file):
    suffix = os.path.splitext((uploaded_file.name or "").strip())[1] or ".txt"
    temp_path = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            for chunk in uploaded_file.chunks():
                temp_file.write(chunk)
            temp_path = temp_file.name
        return parse_resume(temp_path)
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

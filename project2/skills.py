import re

from django.apps import apps
from django.db.utils import OperationalError, ProgrammingError


BASE_SKILLS = [
    "Python",
    "Django",
    "Java",
    "JavaScript",
    "TypeScript",
    "C#",
    "C++",
    "SQL",
    "AWS",
    "Azure",
    "GCP",
    "React",
    "Angular",
    "Node.js",
    "REST",
    "GraphQL",
    "Docker",
    "Kubernetes",
    "Git",
    "Machine Learning",
    "Data Analysis",
    "Tableau",
    "Power BI",
    "UI/UX",
    "Product Management",
]
COMMON_SKILLS = BASE_SKILLS

_BASE_SKILL_LOOKUP = {skill.lower(): skill for skill in BASE_SKILLS}
_DEFAULT_SKILL_DISPLAY_LOOKUP = {
    skill.lower(): skill
    for skill in BASE_SKILLS
}
_DEFAULT_SKILL_DISPLAY_LOOKUP.update(
    {
        "android": "Android",
        "ansible": "Ansible",
        "aws": "AWS",
        "bash": "Bash",
        "ci/cd": "CI/CD",
        "confluence": "Confluence",
        "c#": "C#",
        "c++": "C++",
        "cypress": "Cypress",
        "digitalocean": "DigitalOcean",
        "dynamodb": "DynamoDB",
        "express": "Express",
        "fastapi": "FastAPI",
        "figma": "Figma",
        "flask": "Flask",
        "flutter": "Flutter",
        "gcp": "GCP",
        "github actions": "GitHub Actions",
        "gitlab ci": "GitLab CI",
        "go": "Go",
        "graphql": "GraphQL",
        "heroku": "Heroku",
        "ios": "iOS",
        "jenkins": "Jenkins",
        "jira": "Jira",
        "jupyter": "Jupyter",
        "kubernetes": "Kubernetes",
        "langchain": "LangChain",
        "linux": "Linux",
        "microservices": "Microservices",
        "mlflow": "MLflow",
        "mongodb": "MongoDB",
        "mysql": "MySQL",
        "next.js": "Next.js",
        "node.js": "Node.js",
        "numpy": "NumPy",
        "nuxt.js": "Nuxt.js",
        "php": "PHP",
        "postgresql": "PostgreSQL",
        "postman": "Postman",
        "pytest": "PyTest",
        "pytorch": "PyTorch",
        "react native": "React Native",
        "rest api": "REST API",
        "scikit-learn": "scikit-learn",
        "selenium": "Selenium",
        "snowflake": "Snowflake",
        "spring": "Spring",
        "sql": "SQL",
        "sqlite": "SQLite",
        "svelte": "Svelte",
        "tensorflow": "TensorFlow",
        "testing": "Testing",
        "vite": "Vite",
        "vue": "Vue",
        "webpack": "Webpack",
    }
)


def _clean_skill_token(raw_value):
    return " ".join((raw_value or "").strip().split())


def _build_skill_display_lookup(custom_skills=None):
    lookup = dict(_DEFAULT_SKILL_DISPLAY_LOOKUP)
    skills = get_custom_skill_options() if custom_skills is None else custom_skills
    for skill in skills:
        normalized = _clean_skill_token(skill)
        if not normalized:
            continue
        key = normalized.lower()
        if key in lookup:
            continue
        lookup[key] = normalized
    return lookup


def get_skill_display_lookup():
    return _build_skill_display_lookup()


def normalize_skill_name(raw_value, *, display_lookup=None):
    skill = _clean_skill_token(raw_value)
    if not skill:
        return ""

    lookup = display_lookup if display_lookup is not None else get_skill_display_lookup()
    normalized = lookup.get(skill.lower())
    if normalized:
        return normalized

    if skill == skill.lower() and re.fullmatch(r"[a-z]+(?:[ -][a-z]+)*", skill):
        parts = []
        for word in skill.split():
            parts.append("-".join(piece.capitalize() for piece in word.split("-")))
        return " ".join(parts)

    return skill


def split_skills_csv(raw_value):
    if not raw_value:
        return []

    normalized = []
    seen = set()
    display_lookup = get_skill_display_lookup()
    chunks = str(raw_value).replace(";", ",").split(",")
    for chunk in chunks:
        skill = normalize_skill_name(chunk, display_lookup=display_lookup)
        if not skill:
            continue
        key = skill.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(skill)

    return normalized


def _skill_option_model():
    try:
        return apps.get_model("accounts", "SkillOption")
    except (LookupError, ValueError):
        return None


def get_custom_skill_options():
    model = _skill_option_model()
    if model is None:
        return []

    try:
        return list(model.objects.order_by("name").values_list("name", flat=True))
    except (OperationalError, ProgrammingError):
        return []


def get_skill_options():
    custom_skills = get_custom_skill_options()
    display_lookup = _build_skill_display_lookup(custom_skills)
    options = list(BASE_SKILLS)
    seen = {skill.lower() for skill in options}
    for skill in custom_skills:
        skill = normalize_skill_name(skill, display_lookup=display_lookup)
        key = skill.lower()
        if key in seen:
            continue
        seen.add(key)
        options.append(skill)
    return options


def register_skill_options(raw_value, created_by=None):
    model = _skill_option_model()
    if model is None:
        return []

    created = []
    for skill in split_skills_csv(raw_value):
        normalized_name = skill.lower()
        if normalized_name in _BASE_SKILL_LOOKUP:
            continue
        try:
            option, was_created = model.objects.get_or_create(
                normalized_name=normalized_name,
                defaults={
                    "name": skill,
                    "created_by": created_by,
                },
            )
        except (OperationalError, ProgrammingError):
            return created
        if was_created:
            created.append(option)
    return created


def merge_skills_csv(*raw_values):
    combined = []
    seen = set()
    for raw_value in raw_values:
        for skill in split_skills_csv(raw_value):
            key = skill.lower()
            if key in seen:
                continue
            seen.add(key)
            combined.append(skill)
    return ", ".join(combined)


def normalize_skills_csv(raw_value):
    return ", ".join(split_skills_csv(raw_value))

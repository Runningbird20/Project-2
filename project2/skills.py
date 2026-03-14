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


def _clean_skill_token(raw_value):
    return " ".join((raw_value or "").strip().split())


def split_skills_csv(raw_value):
    if not raw_value:
        return []

    normalized = []
    seen = set()
    chunks = str(raw_value).replace(";", ",").split(",")
    for chunk in chunks:
        skill = _clean_skill_token(chunk)
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
    options = list(BASE_SKILLS)
    seen = {skill.lower() for skill in options}
    for skill in get_custom_skill_options():
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

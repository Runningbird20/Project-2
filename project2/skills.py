COMMON_SKILLS = [
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


def normalize_skills_csv(raw_value):
    if not raw_value:
        return ""

    normalized = []
    seen = set()
    chunks = str(raw_value).replace(";", ",").split(",")
    for chunk in chunks:
        skill = chunk.strip()
        if not skill:
            continue
        key = skill.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(skill)

    return ", ".join(normalized)

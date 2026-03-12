import PyPDF2
import re

SKILL_LIBRARY = {
    "python": ["python", "python3", "python programming"],
    "javascript": ["javascript", "js", "nodejs"],
    "react": ["react", "react.js", "reactjs"],
    "django": ["django", "django framework"],
    "sql": ["sql", "postgresql", "mysql"],
}

def extract_text_from_pdf(file_path):
    text = ""
    with open(file_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text += page.extract_text() or ""
    return text

def extract_skills(text):
    found = []
    for canonical, variants in SKILL_LIBRARY.items():
        for v in variants:
            if re.search(rf"\b{re.escape(v)}\b", text, re.IGNORECASE):
                found.append(canonical)
    return list(set(found))

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

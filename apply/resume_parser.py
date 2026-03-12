import PyPDF2
import re

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

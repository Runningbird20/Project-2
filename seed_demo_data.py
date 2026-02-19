#!/usr/bin/env python
import argparse
import os
import random
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project2.settings")

import django  # noqa: E402

django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from django.db import transaction  # noqa: E402

from accounts.models import Profile  # noqa: E402
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

STREET_NAMES = [
    "Peachtree", "Main", "Broad", "Pine", "Oak", "Maple", "Lake",
    "Cedar", "Willow", "Highland", "Park", "Washington",
]

STREET_SUFFIXES = ["St", "Ave", "Blvd", "Rd", "Ln", "Way", "Dr"]

US_CITIES = [
    ("Atlanta", "GA", "30303", 33.7490, -84.3880),
    ("Austin", "TX", "78701", 30.2672, -97.7431),
    ("Seattle", "WA", "98101", 47.6062, -122.3321),
    ("Denver", "CO", "80202", 39.7392, -104.9903),
    ("Chicago", "IL", "60601", 41.8781, -87.6298),
    ("Boston", "MA", "02108", 42.3601, -71.0589),
    ("Miami", "FL", "33101", 25.7617, -80.1918),
    ("Phoenix", "AZ", "85004", 33.4484, -112.0740),
]

WORK_SETTINGS = ["remote", "onsite", "hybrid"]
COMPANY_SIZES = ["small", "mid_size", "large", "startup", "enterprise"]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Populate PandaPulse with demo employers, applicants, job posts, addresses, and skills."
    )
    parser.add_argument("--employers", type=int, default=12, help="Number of employer accounts to create.")
    parser.add_argument("--applicants", type=int, default=30, help="Number of applicant accounts to create.")
    parser.add_argument("--jobs", type=int, default=70, help="Number of job posts to create.")
    parser.add_argument("--password", default="Pass12345!", help="Password used for created users.")
    parser.add_argument("--prefix", default="seed", help="Username/email prefix for generated accounts.")
    parser.add_argument(
        "--clear-prefix",
        action="store_true",
        help="Delete previously generated users/job posts for this prefix before creating new data.",
    )
    return parser.parse_args()


def pick_skills(min_count=3, max_count=7):
    count = random.randint(min_count, max_count)
    return ", ".join(sorted(random.sample(SKILLS, count)))


def random_address():
    city, state, zip_code, base_lat, base_lon = random.choice(US_CITIES)
    line_1 = f"{random.randint(100, 9999)} {random.choice(STREET_NAMES)} {random.choice(STREET_SUFFIXES)}"
    line_2 = ""
    full = f"{line_1}, {city}, {state} {zip_code}, United States"
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
        company_name = random.choice(COMPANY_NAMES)
        address = random_address()
        ensure_profile(
            user,
            Profile.AccountType.EMPLOYER,
            company_name=company_name,
            company_website=f"https://www.{company_name.lower().replace(' ', '')}.com",
            company_description=f"{company_name} is hiring across engineering teams.",
            location=address["full"],
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
            company_name="",
            company_website="",
            company_description="",
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


def clear_seed_data(prefix):
    User = get_user_model()
    users = User.objects.filter(username__startswith=f"{prefix}_")
    user_ids = list(users.values_list("id", flat=True))

    # Remove jobs owned by seeded users first (cascades office locations).
    JobPost.objects.filter(owner_id__in=user_ids).delete()
    users.delete()


def main():
    args = parse_args()
    random.seed()

    with transaction.atomic():
        if args.clear_prefix:
            clear_seed_data(args.prefix)

        employers = create_employers(args.prefix, args.employers, args.password)
        applicants = create_applicants(args.prefix, args.applicants, args.password)
        jobs = create_jobs(args.prefix, employers, args.jobs)

    print("Seed complete.")
    print(f"Created employers: {len(employers)}")
    print(f"Created applicants: {len(applicants)}")
    print(f"Created job posts: {len(jobs)}")
    print(f"Username prefix: {args.prefix}_*")
    print(f"Password: {args.password}")


if __name__ == "__main__":
    main()

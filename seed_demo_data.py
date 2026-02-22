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

COMPANY_PREFIXES = [
    "North", "South", "East", "West", "Summit", "Bright", "Blue", "Green", "Silver",
    "Golden", "Rapid", "Prime", "Quantum", "Nimbus", "Pioneer", "Urban", "Metro",
]

COMPANY_ROOTS = [
    "Harbor", "Bridge", "Labs", "Works", "Systems", "Digital", "Cloud", "Forge",
    "Motion", "Orbit", "Pixel", "Core", "Logic", "Scale", "Trail", "Pulse", "Matrix",
]

COMPANY_SUFFIXES = ["Inc", "Labs", "Tech", "Group", "Co", "Systems"]

STREET_NAMES = [
    "Peachtree", "Main", "Broad", "Pine", "Oak", "Maple", "Lake",
    "Cedar", "Willow", "Highland", "Park", "Washington", "Market",
    "Sunset", "Riverside", "Liberty", "Union", "King", "Madison",
    "Lakeview", "Magnolia", "Elm", "Monroe", "Jefferson", "Hill",
]

STREET_SUFFIXES = ["St", "Ave", "Blvd", "Rd", "Ln", "Way", "Dr"]

UNIT_LABELS = ["Suite", "Floor", "Unit"]

US_ZIP_INDEX = [
    ("30303", "Atlanta", "GA", 33.7490, -84.3880),
    ("30308", "Atlanta", "GA", 33.7715, -84.3856),
    ("78701", "Austin", "TX", 30.2672, -97.7431),
    ("78704", "Austin", "TX", 30.2465, -97.7602),
    ("98101", "Seattle", "WA", 47.6062, -122.3321),
    ("98104", "Seattle", "WA", 47.6026, -122.3282),
    ("80202", "Denver", "CO", 39.7392, -104.9903),
    ("60601", "Chicago", "IL", 41.8864, -87.6186),
    ("02108", "Boston", "MA", 42.3588, -71.0637),
    ("33101", "Miami", "FL", 25.7617, -80.1918),
    ("85004", "Phoenix", "AZ", 33.4510, -112.0685),
    ("94103", "San Francisco", "CA", 37.7725, -122.4091),
    ("10001", "New York", "NY", 40.7506, -73.9972),
    ("10018", "New York", "NY", 40.7547, -73.9925),
    ("90012", "Los Angeles", "CA", 34.0614, -118.2365),
    ("97204", "Portland", "OR", 45.5190, -122.6765),
    ("37203", "Nashville", "TN", 36.1522, -86.7896),
    ("27601", "Raleigh", "NC", 35.7796, -78.6382),
    ("55401", "Minneapolis", "MN", 44.9833, -93.2676),
    ("84101", "Salt Lake City", "UT", 40.7549, -111.8986),
    ("28202", "Charlotte", "NC", 35.2271, -80.8431),
    ("92101", "San Diego", "CA", 32.7157, -117.1611),
]

WORK_SETTINGS = ["remote", "onsite", "hybrid"]
COMPANY_SIZES = ["small", "mid_size", "large", "startup", "enterprise"]

COMPANY_BLURBS = [
    "builds software products used by teams around the world.",
    "ships cloud infrastructure for fast-growing businesses.",
    "creates AI-powered tools that improve developer productivity.",
    "helps enterprises modernize internal platforms and workflows.",
    "builds secure data products for regulated industries.",
    "develops customer-facing web platforms at scale.",
]

COMPANY_CULTURES = [
    "Ownership-minded team with strong mentorship and clear growth paths.",
    "Collaborative, low-ego culture with emphasis on quality and shipping fast.",
    "Remote-friendly culture focused on transparency and continuous learning.",
    "Product-driven engineering culture with weekly demos and customer feedback loops.",
    "Inclusive team environment with strong documentation and async collaboration.",
]

PERK_POOL = [
    "401(k) match",
    "Home office stipend",
    "Learning budget",
    "Flexible PTO",
    "Parental leave",
    "Commuter benefits",
    "Wellness stipend",
    "Health, dental, vision",
    "Annual team offsite",
    "Performance bonus",
]


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
    parser.add_argument(
        "--clear-only",
        action="store_true",
        help="Delete previously generated users/job posts for this prefix and exit without creating new data.",
    )
    return parser.parse_args()


def pick_skills(min_count=3, max_count=7):
    count = random.randint(min_count, max_count)
    return ", ".join(sorted(random.sample(SKILLS, count)))


def random_address():
    zip_code, city, state, base_lat, base_lon = random.choice(US_ZIP_INDEX)
    line_1 = f"{random.randint(100, 9999)} {random.choice(STREET_NAMES)} {random.choice(STREET_SUFFIXES)}"
    line_2 = ""
    if random.random() < 0.45:
        line_2 = f"{random.choice(UNIT_LABELS)} {random.randint(2, 25)}{random.choice(['', 'A', 'B'])}"
    full = f"{line_1}, {city}, {state} {zip_code}, United States"
    if line_2:
        full = f"{line_1}, {line_2}, {city}, {state} {zip_code}, United States"
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


def random_company_name():
    if random.random() < 0.55:
        return random.choice(COMPANY_NAMES)
    return f"{random.choice(COMPANY_PREFIXES)} {random.choice(COMPANY_ROOTS)} {random.choice(COMPANY_SUFFIXES)}"


def random_company_website(company_name):
    compact = "".join(ch for ch in company_name.lower() if ch.isalnum())
    suffix = random.choice([".com", ".io", ".tech", ".co"])
    return f"https://www.{compact}{suffix}"


def random_company_perks():
    picks = random.sample(PERK_POOL, random.randint(3, 5))
    return "\n".join(picks)


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
        company_name = random_company_name()
        address = random_address()
        ensure_profile(
            user,
            Profile.AccountType.EMPLOYER,
            company_name=company_name,
            company_website=random_company_website(company_name),
            company_description=f"{company_name} {random.choice(COMPANY_BLURBS)}",
            company_culture=random.choice(COMPANY_CULTURES),
            company_perks=random_company_perks(),
            location=address["full"],
            address_line_1=address["line_1"],
            address_line_2=address["line_2"],
            city=address["city"],
            state=address["state"],
            postal_code=address["postal_code"],
            country=address["country"],
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
            address_line_1=address["line_1"],
            address_line_2=address["line_2"],
            city=address["city"],
            state=address["state"],
            postal_code=address["postal_code"],
            country=address["country"],
            company_name="",
            company_website="",
            company_description="",
            company_culture="",
            company_perks="",
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
    deleted_jobs, _ = JobPost.objects.filter(owner_id__in=user_ids).delete()
    deleted_users, _ = users.delete()
    return deleted_users, deleted_jobs


def main():
    args = parse_args()
    random.seed()

    with transaction.atomic():
        if args.clear_prefix or args.clear_only:
            deleted_users, deleted_jobs = clear_seed_data(args.prefix)
            print(f"Deleted users: {deleted_users}")
            print(f"Deleted jobs/related rows: {deleted_jobs}")
            if args.clear_only:
                print(f"Cleanup complete for prefix: {args.prefix}_*")
                return

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

<div align="center">
  <img src="project2/static/mascot/logo.png" alt="PandaPulse Logo" width="180"/>

  # PandaPulse

  **A full-stack AI-powered job marketplace connecting applicants and employers**

  ![Django](https://img.shields.io/badge/Django-6.0.2-092E20?style=flat&logo=django&logoColor=white)
  ![Python](https://img.shields.io/badge/Python-3.x-3776AB?style=flat&logo=python&logoColor=white)
  ![OpenAI](https://img.shields.io/badge/OpenAI-Integrated-412991?style=flat&logo=openai&logoColor=white)
  ![Google Maps](https://img.shields.io/badge/Google_Maps-API-4285F4?style=flat&logo=googlemaps&logoColor=white)
  ![Tests](https://img.shields.io/badge/Tests-136%2B-brightgreen?style=flat)
  ![License](https://img.shields.io/badge/License-MIT-blue?style=flat)

  *Built as a team capstone project for CS 2340 at Georgia Tech*
</div>

---

## Overview

PandaPulse is a two-sided job marketplace built with Django that goes well beyond a standard job board. It features an **AI career assistant** with function-calling tools, **intelligent skill-based matching**, **geospatial job search**, a **social video pulse feed**, full **interview scheduling workflows**, and rich **application pipeline tracking** — all within a single cohesive platform.

The platform serves two user types simultaneously:
- **Job Seekers** — discover jobs, track applications, get AI-powered coaching, and build a visible profile
- **Employers** — post jobs, manage candidates in a visual pipeline, schedule interviews, and send offer letters

---

## Features

### For Job Seekers

| Feature | Details |
|---|---|
| **Smart Profile Builder** | Skills, experience, education, projects, and profile links (GitHub, portfolio) |
| **Resume Parsing** | Upload a PDF resume and automatically extract skills from a 100+ item skill library |
| **Job Matching** | Receive email notifications when a new job matches 50%+ of your skill set |
| **Application Tracker** | Visual pipeline showing status: Applied → Review → Interview → Offer → Closed |
| **Private Notes** | Annotate any application with notes only you can see |
| **Interview Scheduling** | View proposed time slots, book a session, and download `.ics` calendar events |
| **Offer Letters** | Receive and review employer-sent offer letters directly on the platform |
| **Map-Based Job Search** | Find jobs near you with address input and configurable distance radius |
| **Panda Assistant** | AI chatbot that can update your profile, search jobs, and send messages on your behalf |
| **Video Pulses** | Share career updates to a social feed visible to your network |
| **Direct Messaging** | Chat with employers with real-time typing indicators and read receipts |

### For Employers

| Feature | Details |
|---|---|
| **Job Posting** | Create detailed listings with pay range, description, location, and skill requirements |
| **Applicant Pipeline** | Drag-and-drop-style status management across 6 pipeline stages |
| **Candidate Discovery** | AI-surfaced candidate recommendations based on skill overlap |
| **Private Notes** | Annotate candidates with hiring notes only your team can see |
| **Interview Scheduling** | Propose multiple time slots; the system prevents double-booking atomically |
| **Interview Feedback** | Score candidates on technical skill, communication, and problem-solving |
| **Skill Endorsements** | Endorse applicant skills after an interview to strengthen their profile |
| **Offer Letters** | Draft and send customizable offer letters with compensation and start date |
| **Rejection Feedback** | Send structured rejection reasons with pre-built templates |
| **Response SLA Tracking** | Automatically displays average response time to applicants ("Responds in ~2 days") |
| **Cluster Map** | Visualize geographic distribution of your applicant pool on an interactive map |
| **CSV Export** | Export full application pipelines to CSV for offline analysis |

### AI — Panda Assistant

The built-in AI assistant (powered by OpenAI / OpenRouter) goes beyond a simple chatbot:

- **Function Calling** — the assistant can take real actions: update profile fields, apply to jobs, search listings, send messages, and create job postings
- **Live Context Injection** — each session is seeded with the user's live data: unread messages, upcoming interviews, recent pulses, profile completeness score, and current job matches
- **Conversation Memory** — session-based memory persists across page reloads
- **Feedback Loop** — thumbs up/down on each response for quality tracking
- **Dual Role Awareness** — separate tool sets and workflows for applicant vs. employer accounts

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Django 6.0.2, Python |
| **Database** | SQLite (Django ORM) |
| **AI / LLM** | OpenAI SDK (≥1.0, <2.0), OpenRouter API |
| **Resume Parsing** | PyPDF (≥5.0) |
| **Image Handling** | Pillow (≥10.0) |
| **Maps & Geocoding** | Google Maps JavaScript API, Google Geocoding API |
| **Email** | Gmail SMTP (configurable via environment variables) |
| **Auth** | Django `contrib.auth` with password reset flows |
| **Frontend** | Django Templates, HTML/CSS, vanilla JS |
| **Testing** | Django `TestCase` (136+ tests across 21 modules) |

---

## Architecture

The project is organized into **9 Django apps**, each owning a distinct domain:

```
pandapulse/
├── accounts/       # User profiles, auth, candidate search, company profiles, saved searches
├── jobposts/       # Job creation, listing, search, and skill-based matching engine
├── apply/          # Applications, pipeline tracking, offer letters, rejection feedback
├── interviews/     # Interview scheduling, slot booking, feedback scoring, ICS export
├── messaging/      # Direct messages, inbox, read status, typing indicators
├── chatbot/        # Panda Assistant (OpenAI function-calling, context injection, feedback)
├── map/            # Office geocoding, job map view, distance filtering
├── pulses/         # Video pulse upload and social feed
└── home/           # Landing page, about page
```

---

## Notable Implementation Details

**Skill-Based Matching Engine** — when a new job is posted or a profile is updated, the system computes pairwise skill overlap between all candidates and jobs, triggers match notifications above a configurable threshold, and surfaces recommendations in both the applicant dashboard and the employer candidate discovery view.

**Atomic Interview Booking** — when a candidate selects a time slot, a database transaction atomically marks it booked and cancels all other pending slots for that interview to prevent race conditions and double-booking.

**PDF Resume Skill Extraction** — uploaded resumes are parsed with PyPDF, then scanned against a curated dictionary of 100+ skills spanning languages, frameworks, databases, and cloud platforms. Matched skills are persisted directly to the user profile.

**Haversine Distance Filtering** — map-based job search uses the Haversine formula to compute great-circle distance between the user's address and each office location, filtering results by a user-specified radius.

**AI Context Injection** — the Panda Assistant system prompt is built dynamically at request time, incorporating the user's current profile completeness, unread message count, active job matches, upcoming interview schedule, and recent pulse activity so responses are always grounded in live data.

---

## Getting Started

### Prerequisites
- Python 3.10+
- A Google Maps API key (for map features)
- An OpenAI or OpenRouter API key (for Panda Assistant)

### Installation

```bash
# Clone the repository
git clone https://github.com/AzureRaven25/Project-2.git
cd Project-2

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your API keys (OPENAI_API_KEY, GOOGLE_MAPS_API_KEY, email credentials)

# Apply migrations
python manage.py migrate

# (Optional) Load demo data
python manage.py seed_data

# Start the development server
python manage.py runserver
```

Visit `http://127.0.0.1:8000` to view the app.

### Running Tests

```bash
python manage.py test
```

136+ tests across accounts, applications, job posts, messaging, maps, chatbot, and pulses.

---

## Team

Built by a team of Georgia Tech CS students for CS 2340 (Objects and Design), Spring 2025.


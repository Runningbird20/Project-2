from urllib.parse import parse_qs, quote, urlsplit

from django.urls import Resolver404, resolve
from django.utils.http import url_has_allowed_host_and_scheme


VIEW_LABELS = {
    "home.index": "Home",
    "jobposts.search": "Open Positions",
    "jobposts.detail": "Job Details",
    "jobposts.create": "Open Positions",
    "jobposts.edit": "Open Positions",
    "jobposts.edit_post": "Open Positions",
    "accounts.profile": "Profile",
    "accounts.profile_edit": "Profile",
    "accounts.public_profile": "Candidate Profile",
    "accounts.candidate_search": "Find Candidates",
    "accounts.company_search": "Company Search",
    "accounts.company_profile": "Company Profile",
    "accounts.company_profile_edit": "Company Profile",
    "accounts.manage_users": "Manage Users",
    "accounts.applicant_clusters_map": "Find Candidates",
    "accounts.email_candidate": "Candidate Profile",
    "map.jobs_map": "Jobs Map",
    "map.job_location": "Map",
    "apply:application_status": "Dashboard",
    "apply:application_submitted": "Open Positions",
    "apply:employer_pipeline": "Pipeline",
    "apply:offer_letter": "Offer Letter",
    "apply:customize_offer_letter": "Pipeline",
}

DASHBOARD_TAB_LABELS = {
    "emp-listings": "Open Positions",
    "emp-matches": "Find Candidates",
    "emp-tools": "More Tools",
    "emp-interviews": "Interviews",
    "emp-archived": "Archived Applicants",
    "emp-profile": "Dashboard",
}


def safe_local_navigation_url(request, candidate_url):
    candidate_url = (candidate_url or "").strip()
    if not candidate_url:
        return ""
    if not url_has_allowed_host_and_scheme(
        candidate_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return ""

    parsed = urlsplit(candidate_url)
    safe_url = parsed.path or "/"
    if parsed.query:
        safe_url = f"{safe_url}?{parsed.query}"
    if parsed.fragment:
        safe_url = f"{safe_url}#{parsed.fragment}"
    return safe_url


def current_request_url(request):
    return safe_local_navigation_url(request, request.get_full_path()) or "/"


def navigation_label_for_url(url, default_label="Dashboard"):
    parsed = urlsplit((url or "").strip())
    path = parsed.path or "/"
    query = parse_qs(parsed.query)

    try:
        match = resolve(path)
    except Resolver404:
        return default_label

    if match.view_name == "jobposts.dashboard":
        tab = (query.get("tab") or [""])[0]
        return DASHBOARD_TAB_LABELS.get(tab, "Dashboard")

    return VIEW_LABELS.get(match.view_name, default_label)


def build_back_navigation(
    request,
    default_url,
    *,
    default_label=None,
    return_to=None,
    blocked_urls=None,
    blocked_prefixes=None,
):
    default_url = safe_local_navigation_url(request, default_url) or "/"
    default_label = default_label or navigation_label_for_url(default_url, "Dashboard")

    current_url = current_request_url(request)
    blocked_url_set = {current_url}
    for blocked_url in blocked_urls or []:
        safe_blocked_url = safe_local_navigation_url(request, blocked_url)
        if safe_blocked_url:
            blocked_url_set.add(safe_blocked_url)

    safe_blocked_prefixes = []
    for blocked_prefix in blocked_prefixes or []:
        safe_blocked_prefix = safe_local_navigation_url(request, blocked_prefix)
        if safe_blocked_prefix:
            safe_blocked_prefixes.append(safe_blocked_prefix)

    candidates = []
    if return_to is None:
        candidates.extend([request.GET.get("return_to"), request.POST.get("return_to")])
    else:
        candidates.append(return_to)
    candidates.append(request.META.get("HTTP_REFERER"))

    target_url = ""
    for candidate in candidates:
        safe_candidate = safe_local_navigation_url(request, candidate)
        if not safe_candidate:
            continue
        if safe_candidate in blocked_url_set:
            continue
        if any(safe_candidate.startswith(prefix) for prefix in safe_blocked_prefixes):
            continue
        target_url = safe_candidate
        break

    if not target_url:
        target_url = default_url

    label = navigation_label_for_url(target_url, default_label)
    return {
        "url": target_url,
        "label": label,
        "text": f"Back to {label}",
        "encoded_url": quote(target_url, safe=""),
    }

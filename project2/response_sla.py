from apply.models import Application


def format_response_time_window(avg_hours):
    if avg_hours < 24:
        rounded_hours = max(1, int(round(avg_hours)))
        label = "hour" if rounded_hours == 1 else "hours"
        return f"~{rounded_hours} {label}"
    rounded_days = max(1, int(round(avg_hours / 24)))
    label = "day" if rounded_days == 1 else "days"
    return f"~{rounded_days} {label}"


def response_sla_tone(avg_hours):
    if avg_hours < 49:
        return "green"
    if avg_hours > 7 * 24:
        return "red"
    return "yellow"


def build_response_sla(avg_hours):
    if avg_hours is None:
        return {
            "label": "Response time unavailable",
            "css_class": "is-neutral",
            "hours": None,
        }
    return {
        "label": f"Responds in {format_response_time_window(avg_hours)}",
        "css_class": f"is-{response_sla_tone(avg_hours)}",
        "hours": round(avg_hours, 1),
    }


def build_response_sla_by_employer_ids(employer_ids):
    owner_ids = [owner_id for owner_id in employer_ids if owner_id]
    if not owner_ids:
        return {}

    aggregates = {owner_id: {"total_hours": 0.0, "count": 0} for owner_id in owner_ids}
    response_rows = Application.objects.filter(
        job__owner_id__in=owner_ids,
        responded_at__isnull=False,
    ).values_list("job__owner_id", "applied_at", "responded_at")

    for owner_id, applied_at, responded_at in response_rows:
        if not applied_at or not responded_at or responded_at < applied_at:
            continue
        delta_hours = (responded_at - applied_at).total_seconds() / 3600
        bucket = aggregates[owner_id]
        bucket["total_hours"] += delta_hours
        bucket["count"] += 1

    sla_by_owner = {}
    for owner_id in owner_ids:
        bucket = aggregates[owner_id]
        avg_hours = None
        if bucket["count"] > 0:
            avg_hours = bucket["total_hours"] / bucket["count"]
        sla_by_owner[owner_id] = build_response_sla(avg_hours)
    return sla_by_owner

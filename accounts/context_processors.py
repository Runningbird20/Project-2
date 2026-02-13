from .models import Profile


def can_post_job(request):
    if not request.user.is_authenticated:
        return {"can_post_job": False}

    is_employer = Profile.objects.filter(
        user=request.user,
        account_type=Profile.AccountType.EMPLOYER,
    ).exists()
    return {"can_post_job": is_employer}

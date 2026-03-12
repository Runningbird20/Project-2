from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import Message
from accounts.models import Profile
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone


def _can_post_job(user):
    profile, _ = Profile.objects.get_or_create(user=user)
    return profile.account_type == Profile.AccountType.EMPLOYER


@login_required
def check_typing_status(request, partner_id):
    partner_profile = get_object_or_404(Profile, user_id=partner_id)
    is_typing = False
    if partner_profile.is_typing and partner_profile.last_typing_update:
        delta = timezone.now() - partner_profile.last_typing_update
        is_typing = delta.total_seconds() < 4
        
    return JsonResponse({'is_typing': is_typing})

@login_required
def update_my_typing_status(request):
    Profile.objects.filter(user=request.user).update(
        is_typing=True, 
        last_typing_update=timezone.now()
    )
    return JsonResponse({'status': 'ok'})

@login_required
def inbox(request):
    can_post_job = _can_post_job(request.user)
    sent_to = Message.objects.filter(sender=request.user).values_list('recipient', flat=True)
    received_from = Message.objects.filter(recipient=request.user).values_list('sender', flat=True)
    
    partner_ids = set(list(sent_to) + list(received_from))
    
    threads = []
    partners = User.objects.filter(id__in=partner_ids).select_related('profile')
    
    for partner in partners:
        last_message = Message.objects.filter(
            Q(sender=request.user, recipient=partner) | 
            Q(sender=partner, recipient=request.user)
        ).latest('timestamp')
        
        unread_count = Message.objects.filter(
            sender=partner, 
            recipient=request.user, 
            is_read=False
        ).count()
        
        threads.append({
            'partner': partner,
            'last_message': last_message,
            'unread_count': unread_count
        })

    threads.sort(key=lambda x: x['last_message'].timestamp, reverse=True)
    return render(request, 'messaging/inbox.html', {
        'chat_threads': threads,
        'can_post_job': can_post_job,
    })

@login_required
def chat_detail(request, partner_id):
    partner = get_object_or_404(User, id=partner_id)
    can_post_job = _can_post_job(request.user)
    partner_profile, _ = Profile.objects.get_or_create(user=partner)
    partner_public_username = ""
    if can_post_job and partner_profile.account_type == Profile.AccountType.APPLICANT:
        partner_public_username = partner.username
    
    messages = Message.objects.filter(
        Q(sender=request.user, recipient=partner) | 
        Q(sender=partner, recipient=request.user)
    ).order_by('timestamp')
    
    messages.filter(recipient=request.user, is_read=False).update(is_read=True)

    if request.method == 'POST':
        body = request.POST.get('body')
        if body:
            Message.objects.create(sender=request.user, recipient=partner, body=body)
            Profile.objects.filter(user=request.user).update(is_typing=False)
            return redirect('messaging:chat_detail', partner_id=partner_id)

    return render(request, 'messaging/chat_detail.html', {
        'partner': partner,
        'chat_messages': messages,
        'can_post_job': can_post_job,
        'partner_public_username': partner_public_username,
    })

@login_required
def send_message(request, recipient_id):
    recipient = get_object_or_404(User, id=recipient_id)
    
    if request.method == 'POST':
        body = request.POST.get('body')
        if body:
            Message.objects.create(sender=request.user, recipient=recipient, body=body)
            return redirect('messaging:chat_detail', partner_id=recipient_id)
            
    return redirect('messaging:chat_detail', partner_id=recipient_id)

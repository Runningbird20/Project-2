import openai
import json
from django.http import StreamingHttpResponse, JsonResponse
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db.models import Avg, Max

from .models import ChatFeedback
from jobposts.models import JobPost, ApplicantJobMatch
from apply.models import Application
from messaging.models import Message

def get_comprehensive_site_context(user):
    """Gathers data concisely. Fixed: Removed .subject and used .body only."""
    unread_count = Message.objects.filter(recipient=user, is_read=False).count()
    
    # Get unread message snippets safely using only the body
    unread_msgs = Message.objects.filter(recipient=user, is_read=False).order_by('-timestamp')[:3]
    
    msg_details = []
    for m in unread_msgs:
        # Provide more of the body (150 chars) so the AI has actual content to read
        snippet = f"From {m.sender.username}: '{m.body[:150]}...'"
        msg_details.append(snippet)

    user_apps = Application.objects.filter(user=user).values_list('job_id', flat=True)
    
    # Get top 3 matches instead of every job
    matches = ApplicantJobMatch.objects.filter(applicant=user).select_related('job').order_by('-score')[:3]
    match_list = [f"{m.job.title} at {m.job.company} [ID:{m.job.id}]" for m in matches]

    context = (
        f"USER_NAME: {user.username}\n"
        f"UNREAD_MESSAGES_COUNT: {unread_count}\n"
        f"MESSAGE_CONTENTS: {msg_details if unread_count > 0 else 'None'}\n"
        f"TOP_JOB_MATCHES: {match_list}\n"
    )
    return context

@login_required
def ask_panda(request):
    if request.method == "POST":
        user_message = request.POST.get('message')
        site_knowledge = get_comprehensive_site_context(request.user)
        first_name = request.user.first_name or request.user.username

        # REFINED SYSTEM PROMPT: Strict rules to stop the repetition loop
        system_content = (
            f"You are the PandaPulse Career Copilot. User: {first_name}.\n"
            f"--- CURRENT SITE DATA ---\n{site_knowledge}\n"
            f"--- OPERATING RULES ---\n"
            f"1. DIRECT ACTION: If the user asks to 'read', 'show', or 'open' messages, use the MESSAGE_CONTENTS provided above immediately.\n"
            f"2. NO GREETING LOOPS: Do not say 'Welcome', 'Your name is...', or 'Glad to have you' in every message. Just answer the question.\n"
            f"3. CONTEXTUAL: If the user says 'read it', they are referring to the unread messages in SITE DATA.\n"
            f"4. JOBS: Only list jobs if specifically asked or if relevant to a career query. Use [APPLY:ID] tags.\n"
            f"5. BE CONCISE: Stick to the facts in the DATA section. Do not hallucinate message subjects."
        )

        if 'chat_history' not in request.session:
            request.session['chat_history'] = []
        
        history = request.session['chat_history']
        
        # Build the payload
        messages = [{"role": "system", "content": system_content}]
        # Limit history to 5 messages to prevent context drifting back into old greetings
        messages.extend(history[-5:]) 
        messages.append({"role": "user", "content": user_message})

        client = openai.OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.OPENROUTER_API_KEY
        )

        def stream_generator():
            full_response = ""
            try:
                stream = client.chat.completions.create(
                    model="openrouter/auto", 
                    messages=messages,
                    stream=True,
                    temperature=0.3, # Low temperature keeps it focused on the data provided
                )
                
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_response += content
                        yield content
                
                # Save to history
                history.append({"role": "user", "content": user_message})
                history.append({"role": "assistant", "content": full_response})
                request.session['chat_history'] = history[-10:]
                request.session.modified = True
            
            except Exception as e:
                yield f"Panda Error: {str(e)}"

        return StreamingHttpResponse(stream_generator(), content_type='text/plain')
    
@login_required
@require_POST
def add_skill(request):
    new_skill = request.POST.get('skill', '').strip()
    if not new_skill:
        return JsonResponse({'status': 'error'}, status=400)
    
    profile = request.user.profile
    current = profile.skills if profile.skills else ""
    if new_skill.lower() not in current.lower():
        profile.skills = f"{current}, {new_skill}".strip(", ")
        profile.save()
        # Clear history so the Panda notices the new skill context
        if 'chat_history' in request.session:
            del request.session['chat_history']
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'exists'})

@login_required
@require_POST
def chat_apply(request, job_id):
    try:
        job = JobPost.objects.get(id=job_id)
        if Application.objects.filter(job=job, user=request.user).exists():
            return JsonResponse({'status': 'already_applied'})
        
        Application.objects.create(
            job=job, 
            user=request.user,
            resume_type="profile", 
            status="applied",
            note="Applied via Career Copilot."
        )
        return JsonResponse({'status': 'success'})
    except JobPost.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Job not found'}, status=404)

@login_required
def panda_greet(request):
    """Initial greeting when the chat window is first opened."""
    try:
        name = request.user.first_name or request.user.username
        client = openai.OpenAI(base_url="https://openrouter.ai/api/v1", api_key=settings.OPENROUTER_API_KEY)
        response = client.chat.completions.create(
            model="openrouter/auto",
            messages=[{"role": "system", "content": f"Warmly greet {name} as a career panda assistant. Keep it under 12 words."}],
            temperature=0.7
        )
        greeting = response.choices[0].message.content
    except:
        greeting = f"Hi {name}! I'm your Career Panda. How can I help you today?"
    return JsonResponse({'greeting': greeting})

@login_required
def clear_history(request):
    if 'chat_history' in request.session:
        del request.session['chat_history']
        request.session.modified = True
    return JsonResponse({'status': 'cleared'})

@login_required
def save_feedback(request):
    if request.method == "POST":
        rating = request.POST.get('rating')
        is_positive = (rating == 'up')
        history = request.session.get('chat_history', [])
        if len(history) >= 2:
            ChatFeedback.objects.create(
                user=request.user,
                user_query=history[-2].get('content', ''),
                ai_response=history[-1].get('content', ''),
                is_positive=is_positive
            )
            return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)
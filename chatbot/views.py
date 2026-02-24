import openai
import json
from django.http import JsonResponse
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.contrib.auth.models import User

# Importing models and local utilities
from .models import ChatFeedback
from .tools import CHATBOT_TOOLS
from .utils import get_comprehensive_site_context
from jobposts.models import JobPost
from apply.models import Application
from messaging.models import Message

@login_required
def ask_panda(request):
    if request.method != "POST":
        return JsonResponse({'status': 'error', 'message': 'Only POST allowed'}, status=405)

    user_message = request.POST.get('message')
    if not user_message:
        return JsonResponse({'status': 'error', 'message': 'Empty message'}, status=400)

    if not settings.OPENROUTER_API_KEY:
        return JsonResponse({
            'status': 'error',
            'response': "Panda Assistant is not configured yet. Add OPENROUTER_API_KEY to your .env and restart the server."
        }, status=200)

    # 1. Initialize or Retrieve Conversation History from Session
    # This keeps the "memory" alive across page reloads
    messages = request.session.get('chat_history', [])

    # 2. Gather live site data for the current system prompt
    site_knowledge = get_comprehensive_site_context(request.user)
    profile = request.user.profile
    role_flag = f"USER_ROLE: {profile.account_type}"
    company_flag = f"USER_COMPANY: {profile.company_name}" if profile.account_type == "EMPLOYER" else ""

    # 3. Add/Update System Prompt (Always at index 0 to stay current with site state)
    system_prompt = {
        "role": "system", 
        "content": (
            f"You are the PandaPulse Supreme Career Agent. You are an expert career coach.\n"
            f"--- IDENTITY ---\n{role_flag}\n{company_flag}\n"
            f"--- SITE DATA ---\n{site_knowledge}\n"
            "\n--- PROTOCOL ---\n"
            "1. Use Markdown. 2. Call tools immediately. 3. Remember previous context."
        )
    }

    if not messages:
        messages.append(system_prompt)
    else:
        # Refresh the site context in the system prompt if it already exists
        messages[0] = system_prompt

    # Add the new user message to history
    messages.append({"role": "user", "content": user_message})

    client = openai.OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=settings.OPENROUTER_API_KEY
    )

    try:
        # 4. THE AGENTIC LOOP
        for _ in range(5):
            response = client.chat.completions.create(
                model="openrouter/auto",
                messages=messages,
                tools=CHATBOT_TOOLS,
                tool_choice="auto"
            )

            response_message = response.choices[0].message
            
            # Convert the OpenAI object to a serializable dict for session storage
            msg_dict = {
                "role": "assistant",
                "content": response_message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    } for tc in response_message.tool_calls
                ] if response_message.tool_calls else None
            }
            messages.append(msg_dict)

            if not response_message.tool_calls:
                break
            
            # 5. TOOL DISPATCHER
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                tool_result = ""

                if function_name == "update_profile":
                    for key, value in args.items():
                        if hasattr(profile, key): setattr(profile, key, value)
                    profile.save()
                    tool_result = f"Success: Updated {list(args.keys())}."

                elif function_name == "submit_job_application":
                    try:
                        job = JobPost.objects.get(id=args.get("job_id"))
                        app, created = Application.objects.get_or_create(
                            job=job, user=request.user,
                            defaults={'note': args.get("cover_letter"), 'status': 'applied'}
                        )
                        tool_result = "Success: Applied." if created else "Info: Already applied."
                    except: tool_result = "Error: Job not found."

                elif function_name == "search_jobs":
                    query = args.get('keywords', '')
                    results = JobPost.objects.filter(Q(title__icontains=query) | Q(description__icontains=query))[:5]
                    tool_result = f"Found: {[f'{j.title} (ID:{j.id})' for j in results]}"

                elif function_name == "send_direct_message":
                    try:
                        recipient = User.objects.get(username__iexact=args.get('recipient_username'))
                        Message.objects.create(sender=request.user, recipient=recipient, body=args.get('body'))
                        tool_result = f"Success: Sent to {recipient.username}."
                    except: tool_result = "Error: User not found."

                elif function_name == "create_job_posting":
                    if profile.account_type == "EMPLOYER":
                        new_job = JobPost.objects.create(
                            owner=request.user, title=args.get('title'),
                            company=profile.company_name or "My Company",
                            description=args.get('description')
                        )
                        tool_result = f"Success: Job ID {new_job.id} created."
                    else: tool_result = "Denied: Employer only."

                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": tool_result,
                })

        # 6. Finalize: Save the history back to the session
        # Limit history to last 20 messages to keep session cookies small
        request.session['chat_history'] = messages[-20:]
        request.session.modified = True

        return JsonResponse({'response': messages[-1]['content']})

    except Exception as e:
        print(f"Panda Agent Error: {e}")
        return JsonResponse({
            'status': 'error',
            'response': f"Assistant error: {str(e)}"
        }, status=500)

@login_required
def panda_greet(request):
    """If history exists, return it for reconstruction. Otherwise, send fresh greeting."""
    history = request.session.get('chat_history', [])
    
    if history:
        # Filter for display: only return user/assistant content (ignore tool/system roles)
        display_history = [
            {'sender': 'user' if m['role'] == 'user' else 'panda', 'text': m['content']}
            for m in history if m.get('content') and m['role'] in ['user', 'assistant']
        ]
        return JsonResponse({'history': display_history})

    # No history? Generate fresh greeting
    profile = request.user.profile
    name = request.user.first_name or request.user.username
    greeting = f"Hello {name}! 🐼 I see you're an {profile.account_type.lower()}. How can I help you today?"
    return JsonResponse({'greeting': greeting})

@login_required
def clear_history(request):
    if 'chat_history' in request.session:
        del request.session['chat_history']
    return JsonResponse({'status': 'cleared'})

@login_required
def save_feedback(request):
    return JsonResponse({'status': 'success'})

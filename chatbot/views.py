import openai
import json
from django.http import StreamingHttpResponse, JsonResponse
from django.conf import settings
from django.contrib.auth.decorators import login_required
from .models import ChatFeedback

@login_required
def ask_panda(request):
    if request.method == "POST":
        user_message = request.POST.get('message')
        # Check if debug mode was toggled in the UI
        debug_mode = request.POST.get('debug') == 'true'
        
        # 1. Fetch User Profile Data for Context
        try:
            user_profile = request.user.profile
            bio = user_profile.bio if user_profile.bio else "No bio written yet."
            skills = user_profile.skills if user_profile.skills else "No skills listed."
            exp = user_profile.experience_years if user_profile.experience_years else "0"
            first_name = request.user.first_name if request.user.first_name else request.user.username
            last_name = request.user.last_name if request.user.last_name else ""
        except AttributeError:
            bio, skills, exp, first_name, last_name = "None", "None", "0", request.user.username, ""

        # 2. Define the STRICT System Prompt
        # We put this in a variable so we can refresh it every message
        system_content = (
            f"STRICT INSTRUCTIONS: You are the PandaPulse Career Assistant. "
            f"You are talking to {first_name} {last_name}. "
            f"FACTS YOU ALREADY KNOW (DO NOT ASK FOR THESE): "
            f"- User's Name: {first_name} {last_name} "
            f"- User's Current Bio: {bio} "
            f"- User's Skills: {skills} "
            f"- Years of Experience: {exp} "
            f"RULES: "
            f"1. If the user asks for their name, tell them it is {first_name}. "
            f"2. Never say 'I don't know your name' or ask for their skills. "
            f"3. Use the 'Current Bio' provided above if asked to rewrite it. "
            f"4. Wrap suggested profile text in [DRAFT]...[/DRAFT] tags. "
            f"5. Keep responses concise and helpful."
        )

        # 3. Initialize or Refresh Session History
        if 'chat_history' not in request.session:
            request.session['chat_history'] = [{"role": "system", "content": system_content}]
        else:
            # Crucial: Always update the first message (system) to the latest profile data
            request.session['chat_history'][0] = {"role": "system", "content": system_content}
        
        history = request.session['chat_history']
        history.append({"role": "user", "content": user_message})

        # 4. OpenRouter Configuration
        client = openai.OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.OPENROUTER_API_KEY,
            default_headers={
                "HTTP-Referer": "http://127.0.0.1:8000",
                "X-Title": "PandaPulse Assistant",
            }
        )

        def stream_generator():
            # If debug is on, let the developer see exactly what the AI was told
            if debug_mode:
                yield f"**[DEBUG MODE ACTIVE]**\n**System Name injected:** {first_name}\n**Prompt Length:** {len(system_content)} chars\n\n---\n\n"

            full_response = ""
            try:
                stream = client.chat.completions.create(
                    model="openrouter/auto", 
                    messages=history,
                    stream=True,
                    temperature=0.3, # Low temperature = high factual accuracy
                )
                
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_response += content
                        yield content
                
                # Update session with the AI's response
                history.append({"role": "assistant", "content": full_response})
                request.session['chat_history'] = history[-10:] # Context window of 10
                request.session.modified = True
            
            except Exception as e:
                yield f"Panda Error: {str(e)}"

        return StreamingHttpResponse(stream_generator(), content_type='text/plain')

@login_required
def panda_greet(request):
    """Simple non-streaming view for the typewriter greeting"""
    try:
        name = request.user.first_name or request.user.username
        skills = request.user.profile.skills if hasattr(request.user, 'profile') else ""
        
        client = openai.OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.OPENROUTER_API_KEY
        )
        
        response = client.chat.completions.create(
            model="openrouter/auto",
            messages=[{
                "role": "system", 
                "content": f"Greet {name} warmly. Mention their skills ({skills}) briefly. Max 15 words."
            }],
            temperature=0.7 # Greeting can be more creative
        )
        greeting = response.choices[0].message.content
    except Exception:
        greeting = f"Hi {request.user.first_name or request.user.username}! Ready to work on your career?"
        
    return JsonResponse({'greeting': greeting})

@login_required
def clear_history(request):
    """Resets the conversation"""
    if 'chat_history' in request.session:
        del request.session['chat_history']
        request.session.modified = True
    return JsonResponse({'status': 'cleared'})

@login_required
def save_feedback(request):
    """Saves up/down votes to the database"""
    if request.method == "POST":
        rating = request.POST.get('rating')
        is_positive = (rating == 'up')
        history = request.session.get('chat_history', [])
        
        last_user_query = ""
        last_ai_response = ""
        
        if len(history) >= 2:
            last_ai_response = history[-1].get('content', '')
            last_user_query = history[-2].get('content', '')

        ChatFeedback.objects.create(
            user=request.user,
            user_query=last_user_query,
            ai_response=last_ai_response,
            is_positive=is_positive
        )
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)
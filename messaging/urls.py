from django.urls import path
from . import views

app_name = 'messaging'

urlpatterns = [
    path('inbox/', views.inbox, name='inbox'),
    path('send/<int:recipient_id>/', views.send_message, name='send_message'),
    path('chat/<int:partner_id>/', views.chat_detail, name='chat_detail'),
    path('update-typing/', views.update_my_typing_status, name='update_typing'),
    path('check-typing/<int:partner_id>/', views.check_typing_status, name='check_typing'),
]
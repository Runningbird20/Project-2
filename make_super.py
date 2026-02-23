from django.contrib.auth.models import User
user = User.objects.get(username="Ant")
user.is_staff = True
user.is_admin = True
user.is_superuser = True
user.save()



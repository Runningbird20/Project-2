from django.contrib import admin

from .models import JobPost


@admin.register(JobPost)
class JobPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'location', 'work_setting', 'visa_sponsorship', 'created_at')
    search_fields = ('title', 'company', 'location', 'skills')
    list_filter = ('work_setting', 'visa_sponsorship')

from django.contrib import admin

from .models import OfficeLocation
from project2.admin_permissions import StaffReadOnlyAdminMixin


@admin.register(OfficeLocation)
class OfficeLocationAdmin(StaffReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ('job_post', 'city', 'state', 'postal_code', 'latitude', 'longitude')
    search_fields = (
        'job_post__title',
        'job_post__company',
        'address_line_1',
        'city',
        'state',
        'postal_code',
    )

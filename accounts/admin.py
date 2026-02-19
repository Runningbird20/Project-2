from django.contrib import admin
from django.contrib.admin.sites import NotRegistered
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group, User

from project2.admin_permissions import StaffReadOnlyAdminMixin


class ReadOnlyForStaffUserAdmin(StaffReadOnlyAdminMixin, UserAdmin):
    pass


class ReadOnlyForStaffGroupAdmin(StaffReadOnlyAdminMixin, GroupAdmin):
    pass


try:
    admin.site.unregister(User)
except NotRegistered:
    pass

try:
    admin.site.unregister(Group)
except NotRegistered:
    pass

admin.site.register(User, ReadOnlyForStaffUserAdmin)
admin.site.register(Group, ReadOnlyForStaffGroupAdmin)

class StaffReadOnlyAdminMixin:
    """Superusers can manage data; staff users can only view admin pages."""

    def has_module_permission(self, request):
        if request.user.is_superuser:
            return True
        return request.user.is_active and request.user.is_staff

    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return request.user.is_active and request.user.is_staff

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

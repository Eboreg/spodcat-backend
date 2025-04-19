from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from admin_mixin import AdminMixin
from users.models import User


@admin.register(User)
class UserAdmin(AdminMixin, DjangoUserAdmin):
    save_on_top = True

    def get_readonly_fields(self, request, obj=None):
        fields = super().get_readonly_fields(request, obj)
        if not request.user.is_superuser:
            return ["is_superuser", "user_permissions", "groups", *fields]
        return fields

    def has_add_permission(self, request):
        return request.user.is_superuser

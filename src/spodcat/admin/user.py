from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from spodcat.admin.mixins import AdminMixin


try:
    admin.site.unregister(get_user_model())
except Exception:
    pass


@admin.register(get_user_model())
class UserAdmin(AdminMixin, DjangoUserAdmin):
    save_on_top = True

    def get_readonly_fields(self, request, obj=None):
        fields = super().get_readonly_fields(request, obj)
        if not request.user.is_superuser:
            return ["is_superuser", "user_permissions", "groups", *fields]
        return fields

    def has_add_permission(self, request):
        return request.user.is_superuser

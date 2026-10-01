"""Endurecimiento de administradores de registros técnicos de Axes."""
from django.contrib import admin
from django.contrib.admin.sites import NotRegistered
from axes.models import AccessAttempt, AccessFailureLog, AccessLog


class AxesSoloLecturaAdmin(admin.ModelAdmin):
    """Los eventos de bloqueo se consultan; nunca se crean, editan o eliminan."""
    list_display = ('username', 'ip_address', 'attempt_time')
    search_fields = ('username', 'ip_address')
    readonly_fields = ()

    def get_readonly_fields(self, request, obj=None):
        return [campo.name for campo in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


for modelo in (AccessAttempt, AccessFailureLog, AccessLog):
    try:
        admin.site.unregister(modelo)
    except NotRegistered:
        pass
    admin.site.register(modelo, AxesSoloLecturaAdmin)

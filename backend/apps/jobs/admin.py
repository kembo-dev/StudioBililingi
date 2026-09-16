from django.contrib import admin

from .models import Job


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ("project", "kind", "status", "agent_role", "backend", "updated_at")

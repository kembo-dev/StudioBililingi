from django.contrib import admin

from .models import Project, Season


class SeasonInline(admin.TabularInline):
    model = Season
    extra = 0


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "organization", "status")
    inlines = [SeasonInline]

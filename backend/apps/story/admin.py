from django.contrib import admin

from .models import Beat, Episode, Script


@admin.register(Episode)
class EpisodeAdmin(admin.ModelAdmin):
    list_display = ("title", "season", "number", "status")


@admin.register(Script)
class ScriptAdmin(admin.ModelAdmin):
    list_display = ("episode", "version")


@admin.register(Beat)
class BeatAdmin(admin.ModelAdmin):
    list_display = ("episode", "index", "take", "word_count", "status", "backend")

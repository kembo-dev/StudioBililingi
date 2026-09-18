from django.contrib import admin

from .models import Beat, BeatTake, Episode, Scene, Script


@admin.register(Episode)
class EpisodeAdmin(admin.ModelAdmin):
    list_display = ("title", "season", "number", "status")


@admin.register(Script)
class ScriptAdmin(admin.ModelAdmin):
    list_display = ("episode", "version")


@admin.register(Scene)
class SceneAdmin(admin.ModelAdmin):
    list_display = ("episode", "script", "index", "heading", "location")


@admin.register(Beat)
class BeatAdmin(admin.ModelAdmin):
    list_display = ("episode", "script", "index", "word_count", "status", "backend")


@admin.register(BeatTake)
class BeatTakeAdmin(admin.ModelAdmin):
    list_display = ("beat", "number", "backend", "status", "created_at")

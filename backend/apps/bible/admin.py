from django.contrib import admin

from .models import Character, Location, Prop, WorldBible


@admin.register(WorldBible)
class WorldBibleAdmin(admin.ModelAdmin):
    list_display = ("project", "version", "locked")


@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    list_display = ("name", "project", "locked")


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("name", "project", "locked")


@admin.register(Prop)
class PropAdmin(admin.ModelAdmin):
    list_display = ("name", "project", "locked")

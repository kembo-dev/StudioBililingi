from django.contrib import admin

from .models import Asset, Review


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ("project", "kind", "role", "provider")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("decision", "episode", "beat", "beat_take", "created_at")

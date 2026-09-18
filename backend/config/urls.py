from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.projects.views import BeatViewSet, EpisodeViewSet, ProjectViewSet


def health(_request):
    return JsonResponse({"ok": True, "app": "StudioBililingi"})


router = DefaultRouter()
router.register("projects", ProjectViewSet, basename="project")
router.register("episodes", EpisodeViewSet, basename="episode")
router.register("beats", BeatViewSet, basename="beat")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health),
    path("api/", include(router.urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

from rest_framework import serializers

from apps.accounts.models import Organization
from apps.bible.models import Character, Location, Prop, WorldBible
from apps.projects.models import Project, Season
from apps.story.models import Beat, Episode, Script


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ("id", "name", "slug")


class CharacterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Character
        fields = ("id", "key", "name", "role", "want", "need", "look", "voice", "locked")


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ("id", "key", "name", "look", "time_of_day", "locked")


class PropSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prop
        fields = ("id", "key", "name", "look", "story_function", "locked")


class WorldBibleSerializer(serializers.ModelSerializer):
    characters = CharacterSerializer(many=True, read_only=True)
    locations = LocationSerializer(many=True, read_only=True)
    props = PropSerializer(many=True, read_only=True)

    class Meta:
        model = WorldBible
        fields = ("id", "version", "payload", "locked", "created_at", "characters", "locations", "props")


class BeatSerializer(serializers.ModelSerializer):
    clip_uri = serializers.SerializerMethodField()

    class Meta:
        model = Beat
        fields = (
            "id", "index", "take", "text", "word_count", "duration_seconds",
            "emotion", "dialogue", "video_prompt", "backend", "status", "camera", "clip_uri",
        )

    def get_clip_uri(self, obj):
        clip = obj.assets.filter(role="clip").order_by("-id").first()
        return clip.uri if clip else None


class EpisodeSerializer(serializers.ModelSerializer):
    beats = BeatSerializer(many=True, read_only=True)

    class Meta:
        model = Episode
        fields = ("id", "number", "title", "logline", "function_in_arc", "status", "beats")


class SeasonSerializer(serializers.ModelSerializer):
    episodes = EpisodeSerializer(many=True, read_only=True)

    class Meta:
        model = Season
        fields = ("id", "number", "title", "premise", "episodes")


class ProjectSerializer(serializers.ModelSerializer):
    seasons = SeasonSerializer(many=True, read_only=True)
    bibles = WorldBibleSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = ("id", "title", "slug", "concept", "genre", "tone", "ending_intent", "aspect_ratio", "status", "created_at", "seasons", "bibles")
        read_only_fields = ("slug", "status", "created_at")


class ProjectCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    concept = serializers.CharField()
    genre = serializers.CharField(required=False, allow_blank=True, default="")
    tone = serializers.CharField(required=False, allow_blank=True, default="")
    ending_intent = serializers.CharField(required=False, allow_blank=True, default="")
    organization_name = serializers.CharField(required=False, default="Studio")

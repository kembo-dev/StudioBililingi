from rest_framework import serializers

from apps.accounts.models import Organization
from apps.bible.models import Character, Location, Prop, WorldBible
from apps.projects.models import NarrativeContract, NarrativeEvent, Project, Season
from apps.story.models import Beat, BeatTake, Episode, Scene, Script


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


class BeatTakeSerializer(serializers.ModelSerializer):
    class Meta:
        model = BeatTake
        fields = ("id", "number", "prompt", "negative_prompt", "backend", "uri", "status", "generation_meta", "created_at")


class BeatSerializer(serializers.ModelSerializer):
    clip_uri = serializers.SerializerMethodField()
    takes = BeatTakeSerializer(many=True, read_only=True)
    character_ids = serializers.PrimaryKeyRelatedField(source="characters", many=True, read_only=True)
    prop_ids = serializers.PrimaryKeyRelatedField(source="props", many=True, read_only=True)

    class Meta:
        model = Beat
        fields = ("id", "scene_id", "script_id", "narrative_event_id", "index", "take", "text", "word_count", "duration_seconds", "location_id", "character_ids", "speaker_id", "prop_ids", "emotion", "dialogue", "video_prompt", "negative_prompt", "backend", "status", "camera", "continuity", "clip_uri", "takes")

    def get_clip_uri(self, obj):
        locked = obj.takes.filter(status=BeatTake.Status.LOCKED).order_by("-number").first()
        latest = locked or obj.takes.filter(uri__gt="").order_by("-number").first()
        if latest:
            return latest.uri
        clip = obj.assets.filter(role="clip").order_by("-id").first()
        return clip.uri if clip else None


class SceneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scene
        fields = ("id", "script_id", "index", "heading", "summary", "location_id", "time_of_day", "lighting", "continuity_state")


class EpisodeSerializer(serializers.ModelSerializer):
    beats = serializers.SerializerMethodField()
    scenes = serializers.SerializerMethodField()
    latest_script = serializers.SerializerMethodField()

    class Meta:
        model = Episode
        fields = ("id", "number", "title", "logline", "function_in_arc", "status", "beats", "scenes", "latest_script")

    def _latest(self, obj):
        return obj.scripts.order_by("-version").first()

    def get_beats(self, obj):
        script = self._latest(obj)
        return BeatSerializer(script.beats.order_by("index"), many=True).data if script else []

    def get_scenes(self, obj):
        script = self._latest(obj)
        return SceneSerializer(script.scenes.order_by("index"), many=True).data if script else []

    def get_latest_script(self, obj):
        script = obj.scripts.order_by("-version").first()
        return script.fountain if script else ""


class SeasonSerializer(serializers.ModelSerializer):
    episodes = EpisodeSerializer(many=True, read_only=True)

    class Meta:
        model = Season
        fields = ("id", "number", "title", "premise", "episodes")


class NarrativeEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = NarrativeEvent
        fields = ("key", "position", "description", "episode_number", "status")


class NarrativeContractSerializer(serializers.ModelSerializer):
    events = NarrativeEventSerializer(many=True, read_only=True)

    class Meta:
        model = NarrativeContract
        fields = ("point_of_view", "narrator", "tense", "story_type", "recommended_episode_count", "rules", "locked", "events")


class ProjectSerializer(serializers.ModelSerializer):
    seasons = SeasonSerializer(many=True, read_only=True)
    bibles = WorldBibleSerializer(many=True, read_only=True)
    refs = serializers.SerializerMethodField()
    narrative_contract = NarrativeContractSerializer(read_only=True)

    class Meta:
        model = Project
        fields = ("id", "title", "slug", "concept", "genre", "tone", "ending_intent", "aspect_ratio", "delivery", "visual_style", "status", "created_at", "narrative_contract", "seasons", "bibles", "refs")
        read_only_fields = ("slug", "status", "created_at")

    def get_refs(self, obj):
        roles = {"character_ref", "location_ref", "prop_ref"}
        return [
            {"id": asset.id, "role": asset.role, "uri": asset.uri, "provider": asset.provider, "meta": asset.meta}
            for asset in obj.assets.all()
            if asset.role in roles
        ]


class ProjectCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    concept = serializers.CharField()
    genre = serializers.CharField(required=False, allow_blank=True, default="")
    tone = serializers.CharField(required=False, allow_blank=True, default="")
    ending_intent = serializers.CharField(required=False, allow_blank=True, default="")
    delivery = serializers.ChoiceField(choices=("storytell", "voix_off", "conversation", "rencontre"), required=False, default="storytell")
    visual_style = serializers.ChoiceField(choices=Project.VisualStyle.choices, required=False, default=Project.VisualStyle.REALISTIC)
    organization_name = serializers.CharField(required=False, default="Studio")

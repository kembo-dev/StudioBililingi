from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import TestCase

from apps.accounts.models import Organization
from apps.production.models import Review
from apps.projects.assembly import assemble_episode
from apps.projects.models import Project, Season
from apps.projects.character_resolver import CharacterResolver
from apps.projects.services import _canonical_speaker_from_dialogue, _segmentation_errors, _usable_bible, persist_beats, persist_bible, persist_episodes, review_beat
from apps.story.models import Beat, BeatTake, Episode, Script
from apps.bible.models import Character, Location, Prop


class ProductionPipelineTests(TestCase):
    def setUp(self):
        org = Organization.objects.create(name="Test Studio", slug="test-studio")
        self.project = Project.objects.create(
            organization=org,
            title="Test",
            slug="test",
            concept="Concept de test",
            delivery="voix_off",
        )
        self.season = Season.objects.create(project=self.project, number=1)
        self.episode = Episode.objects.create(
            season=self.season,
            number=1,
            title="Episode 1",
            logline="Test",
        )

    def test_resegmentation_preserves_previous_script_and_beats(self):
        first = persist_beats(self.episode, [{"text": "Premier beat", "scene_index": 1}])
        first_id = first[0].id
        first_script_id = first[0].script_id

        second = persist_beats(self.episode, [{"text": "Deuxieme beat", "scene_index": 1}])

        self.assertEqual(Script.objects.filter(episode=self.episode).count(), 2)
        self.assertTrue(Beat.objects.filter(pk=first_id, script_id=first_script_id).exists())
        self.assertNotEqual(second[0].script_id, first_script_id)
        self.assertEqual(self.episode.scenes.count(), 2)

    def test_structured_segmentation_metadata_is_persisted(self):
        beat = persist_beats(self.episode, [{
            "text": "Une action precise",
            "scene_index": 2,
            "scene_heading": "INT. STUDIO - NUIT",
            "time_of_day": "nuit",
            "lighting": "faible",
            "camera": {"shot": "close-up"},
            "continuity": {"wardrobe": "chemise blanche"},
            "emotion": "tension",
            "dialogue": "Allo ?",
            "negative_prompt": "texte incruste",
            "duration_seconds": 6,
        }])[0]

        self.assertEqual(beat.scene.index, 2)
        self.assertEqual(beat.scene.heading, "INT. STUDIO - NUIT")
        self.assertEqual(beat.camera["shot"], "close-up")
        self.assertEqual(beat.continuity["wardrobe"], "chemise blanche")
        self.assertEqual(beat.emotion, "tension")
        self.assertEqual(beat.dialogue, "Allo ?")

    def test_review_locks_exact_take_and_unlocks_previous(self):
        beat = persist_beats(self.episode, [{"text": "Beat"}])[0]
        first = BeatTake.objects.create(beat=beat, number=1, uri="file:///tmp/one.mp4", status=BeatTake.Status.LOCKED)
        second = BeatTake.objects.create(beat=beat, number=2, uri="file:///tmp/two.mp4", status=BeatTake.Status.REVIEW)

        review_beat(beat, "approve", take_id=second.id)

        first.refresh_from_db()
        second.refresh_from_db()
        beat.refresh_from_db()
        self.assertEqual(first.status, BeatTake.Status.REVIEW)
        self.assertEqual(second.status, BeatTake.Status.LOCKED)
        self.assertEqual(beat.take, 2)
        self.assertEqual(beat.status, Beat.Status.LOCKED)
        self.assertTrue(Review.objects.filter(beat_take=second, decision="approve").exists())

    def test_review_refuses_take_without_video(self):
        beat = persist_beats(self.episode, [{"text": "Beat"}])[0]
        take = BeatTake.objects.create(beat=beat, number=1, status=BeatTake.Status.REVIEW)

        with self.assertRaisesMessage(ValueError, "sans vidéo"):
            review_beat(beat, "approve", take_id=take.id)

    def test_assembly_requires_locked_take_for_every_latest_beat(self):
        beats = persist_beats(self.episode, [{"text": "Un"}, {"text": "Deux"}])
        BeatTake.objects.create(beat=beats[0], number=1, uri="file:///tmp/one.mp4", status=BeatTake.Status.LOCKED)

        with self.assertRaisesMessage(ValueError, "aucun take verrouillé"):
            assemble_episode(self.episode)

    def test_assembly_uses_locked_takes_in_beat_order(self):
        beats = persist_beats(self.episode, [{"text": "Un"}, {"text": "Deux"}])
        with TemporaryDirectory() as tmp:
            clips = []
            for i, beat in enumerate(beats):
                path = Path(tmp) / f"{i}.mp4"
                path.write_bytes(b"fake")
                clips.append(path)
                BeatTake.objects.create(
                    beat=beat,
                    number=1,
                    uri=path.as_uri(),
                    status=BeatTake.Status.LOCKED,
                )

            media = Path(tmp) / "media"
            with patch.dict("os.environ", {"STUDIO_MEDIA_ROOT": str(media)}), patch("apps.projects.assembly.subprocess.run") as run:
                asset = assemble_episode(self.episode)

            run.assert_called_once()
            manifest = run.call_args.args[0]
            self.assertEqual(manifest[0], "ffmpeg")
            self.assertEqual(asset.role, "episode_cut")
            self.assertEqual([row["beat_id"] for row in asset.meta["takes"]], [b.id for b in beats])

    def test_showrunner_episode_compact_fields_are_bounded(self):
        episodes = persist_episodes(self.project, [{
            "number": 2,
            "title": "T" * 260,
            "logline": "Une logline longue reste autorisee car le champ est TextField.",
            "function_in_arc": "F" * 350,
        }])

        episode = episodes[0]
        self.assertEqual(len(episode.title), 200)
        self.assertEqual(len(episode.function_in_arc), 200)
        self.assertEqual(
            episode.logline,
            "Une logline longue reste autorisee car le champ est TextField.",
        )

    def test_bible_requires_nonempty_named_character_list(self):
        self.assertFalse(_usable_bible({}))
        self.assertFalse(_usable_bible({"characters": {}}))
        self.assertFalse(_usable_bible({"characters": []}))
        self.assertFalse(_usable_bible({"characters": [{"id": "antoine"}]}))
        self.assertTrue(_usable_bible({
            "characters": [{"id": "antoine", "name": "Antoine"}],
        }))

    def test_bible_compact_fields_are_bounded(self):
        persist_bible(self.project, {
            "characters": [{
                "id": "personnage-" + ("x" * 300),
                "name": "N" * 260,
                "role": "R" * 260,
                "want": "objectif",
                "need": "besoin",
                "look": "look",
                "voice": "voix",
            }],
            "locations": [{
                "id": "lieu-" + ("x" * 300),
                "name": "L" * 260,
                "look": "look",
                "time_of_day": "T" * 160,
            }],
            "props": [{
                "id": "objet-" + ("x" * 300),
                "name": "O" * 260,
                "look": "look",
                "story_function": "F" * 350,
            }],
        })

        character = Character.objects.get(project=self.project)
        location = Location.objects.get(project=self.project)
        prop = Prop.objects.get(project=self.project)
        self.assertEqual(len(character.name), 160)
        self.assertEqual(len(character.role), 160)
        self.assertEqual(len(location.name), 160)
        self.assertEqual(len(location.time_of_day), 80)
        self.assertEqual(len(prop.name), 160)
        self.assertEqual(len(prop.story_function), 200)
        self.assertLessEqual(len(prop.key), Prop._meta.get_field("key").max_length)

    def test_conversation_speaker_resolves_title_case_and_alias(self):
        persist_bible(self.project, {
            "characters": [{
                "id": "antoine-kasongo",
                "name": "Antoine Kasongo",
                "aliases": ["Antoine", "ANTOINE KASONGO"],
                "role": "protagoniste",
                "look": "artisan",
            }],
            "locations": [],
            "props": [],
        })
        resolver = CharacterResolver(self.project)

        self.assertEqual(
            _canonical_speaker_from_dialogue("Antoine : Je reste.", resolver),
            "Antoine Kasongo",
        )
        errors = _segmentation_errors([{
            "text": "Antoine regarde la porte avant de répondre.",
            "dialogue": "Antoine : Je reste.",
            "character_ids": ["antoine-kasongo"],
        }], form="conversation", project=self.project)
        self.assertEqual(errors, [])


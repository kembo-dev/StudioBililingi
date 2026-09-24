from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import TestCase

from apps.accounts.models import Organization
from apps.production.models import Review
from apps.projects.assembly import assemble_episode
from apps.projects.models import NarrativeContract, Project, Season
from apps.projects.character_resolver import CharacterResolver
from apps.projects.beat_normalizer import normalize_beats
from apps.projects.continuity import build_continuity_context, continuity_prompt, validate_render_readiness
from apps.projects.services import _canonical_speaker_from_dialogue, _ensure_script_speakers, _script_speaker_labels, cleanup_generated_script_characters, _segmentation_errors, _usable_bible, persist_beats, persist_bible, persist_episodes, review_beat, plan_beat_shots, review_shot
from apps.story.models import Beat, BeatTake, Episode, Scene, Script, ShotTake
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

    def test_project_delete_cascades_locked_scene_plan_segmentation(self):
        from apps.story.models import ScenePlan, Segmentation
        script = Script.objects.create(episode=self.episode, version=1, fountain="Script")
        plan = ScenePlan.objects.create(
            episode=self.episode, script=script, version=1, locked=True,
            payload=[{"index": 1, "target_seconds": 8}],
        )
        persist_beats(
            self.episode,
            [{"text": "Beat narratif", "scene_index": 1, "duration_seconds": 8}],
            script=script,
            scene_plan=plan,
        )
        project_id = self.project.id
        self.project.delete()
        self.assertFalse(Project.objects.filter(pk=project_id).exists())
        self.assertFalse(Segmentation.objects.filter(scene_plan_id=plan.id).exists())

    def test_resegmentation_preserves_script_and_previous_beats(self):
        # Segmentation versions are independent from screenplay versions:
        # re-segmenting must never manufacture a new Script.
        script = Script.objects.create(
            episode=self.episode,
            version=1,
            fountain="Script canonique",
        )
        first = persist_beats(
            self.episode,
            [{"text": "Premier beat", "scene_index": 1}],
            script=script,
        )
        first_id = first[0].id

        second = persist_beats(
            self.episode,
            [{"text": "Deuxieme beat", "scene_index": 1}],
            script=script,
        )

        self.assertEqual(Script.objects.filter(episode=self.episode).count(), 1)
        self.assertTrue(Beat.objects.filter(pk=first_id, script_id=script.id).exists())
        self.assertEqual(second[0].script_id, script.id)
        self.assertEqual(self.episode.scenes.count(), 2)

    def test_beat_scene_plan_location_ids_are_case_insensitive(self):
        from apps.projects.services import _beat_scene_plan_errors

        errors = _beat_scene_plan_errors(
            [{
                "scene_index": 1,
                "location_id": "GareKinshasa",
                "time_of_day": "Nuit",
                "event_id": "EV01",
            }],
            [{
                "index": 1,
                "location_id": "garekinshasa",
                "time_of_day": "Nuit",
                "event_ids": ["EV01"],
            }],
        )
        self.assertEqual(errors, [])

    def test_scene_plan_normalizes_names_and_llm_aliases_to_canonical_keys(self):
        from apps.projects.services import _canonical_scene_plan_ids

        persist_bible(self.project, {
            "characters": [{"id": "helene-dubois", "name": "Hélène Dubois", "look": "canonique"}],
            "locations": [{"id": "la-gare-centrale-de-kinshasa", "name": "La Gare Centrale de Kinshasa", "look": "canonique"}],
            "props": [
                {"id": "mallette-d-helene", "name": "Mallette d'Hélène", "look": "canonique"},
                {"id": "instrument-de-musique-de-papa-jean", "name": "Instrument de musique de Papa Jean", "look": "canonique"},
                {"id": "banc-de-gare", "name": "Banc de gare", "look": "canonique"},
            ],
        })
        scenes = _canonical_scene_plan_ids([{
            "index": 1,
            "location_id": "GareKinshasa",
            "character_ids": ["Hélène Dubois"],
            "prop_ids": ["BancGare", "InstrumentPapaJean", "MalletteHelene"],
        }], self.project)

        # Exact names are normalized deterministically. Compact aliases remain
        # untouched unless they uniquely match a canonical name/key.
        self.assertEqual(scenes[0]["character_ids"], ["helene-dubois"])
        self.assertEqual(scenes[0]["location_id"], "GareKinshasa")

    def test_long_narrative_beat_can_produce_multiple_shots(self):
        beat = persist_beats(self.episode, [{
            "text": "Malaika explique longuement son echec professionnel pendant que Safia ecoute sans interrompre et lui sert calmement une tasse de the.",
            "scene_index": 1,
            "duration_seconds": 18,
        }])[0]
        planned = {
            "shots": [
                {"index": 1, "text": "Malaika explique son echec.", "video_prompt": "Malaika parle, plan rapproche.", "camera": {}, "continuity": {}},
                {"index": 2, "text": "Safia ecoute sans interrompre.", "video_prompt": "Safia ecoute, champ contrechamp.", "camera": {}, "continuity": {}},
                {"index": 3, "text": "Safia sert une tasse de the.", "video_prompt": "Safia sert le the, insert mains.", "camera": {}, "continuity": {}},
            ]
        }
        with patch("agents.roles.shot_planner.ShotPlanner.plan", return_value=planned):
            shots = plan_beat_shots(beat, max_shot_seconds=8)
        self.assertEqual(len(shots), 3)
        self.assertEqual([float(shot.duration_seconds) for shot in shots], [8.0, 8.0, 8.0])
        self.assertGreaterEqual(sum(float(shot.duration_seconds) for shot in shots), 18.0)
        self.assertTrue(all(float(shot.duration_seconds) == 8.0 for shot in shots))
        self.assertEqual([shot.text for shot in shots], [
            "Malaika explique son echec.",
            "Safia ecoute sans interrompre.",
            "Safia sert une tasse de the.",
        ])
        self.assertTrue(all(shot.continuity["source_beat_text"] == beat.text for shot in shots))

    def test_shot_planning_freezes_reference_uids_before_render(self):
        from apps.production.models import Asset

        persist_bible(self.project, {
            "characters": [{"id": "amina", "name": "Amina", "look": "visage canonique"}],
            "locations": [{"id": "gare", "name": "Gare", "look": "gare canonique"}],
            "props": [{"id": "mallette", "name": "Mallette", "look": "mallette noire"}],
        })
        character = self.project.characters.get(key="amina")
        location = self.project.locations.get(key="gare")
        prop = self.project.props.get(key="mallette")
        for role, key in [
            (Asset.Role.CHARACTER_REF, "amina"),
            (Asset.Role.LOCATION_REF, "gare"),
            (Asset.Role.PROP_REF, "mallette"),
        ]:
            Asset.objects.create(
                project=self.project,
                kind=Asset.Kind.IMAGE,
                role=role,
                uri=f"/tmp/{key}.png",
                meta={"key": key},
            )
        beat = persist_beats(self.episode, [{
            "text": "Amina traverse la gare avec sa mallette.",
            "character_ids": ["amina"],
            "location_id": "gare",
            "prop_ids": ["mallette"],
            "scene_index": 1,
            "duration_seconds": 8,
        }])[0]

        shot = plan_beat_shots(beat)[0]

        self.assertEqual(
            shot.reference_uids,
            [character.reference_uid, location.reference_uid, prop.reference_uid],
        )

    def test_shot_planning_rounds_up_unrepresentable_duration_without_content_loss(self):
        beat = persist_beats(self.episode, [{
            "text": "Le dialogue et l'action restent complets meme si la duree narrative est impaire.",
            "scene_index": 1,
            "duration_seconds": 7,
        }])[0]
        shots = plan_beat_shots(beat)
        self.assertEqual([float(shot.duration_seconds) for shot in shots], [8.0])
        self.assertEqual(shots[0].text, beat.text)
        self.assertEqual(shots[0].continuity["narrative_beat_seconds"], 7.0)

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

    def test_veo_reference_shot_durations_are_always_eight_seconds(self):
        from apps.projects.services import _veo_shot_durations

        self.assertEqual(_veo_shot_durations(1), [8])
        self.assertEqual(_veo_shot_durations(6), [8])
        self.assertEqual(_veo_shot_durations(8), [8])
        self.assertEqual(_veo_shot_durations(9), [8, 8])
        self.assertEqual(_veo_shot_durations(20), [8, 8, 8])

    def test_adjusted_take_uses_previous_take_frame_instead_of_asset_refs(self):
        from unittest.mock import patch
        from apps.projects.services import render_shot
        from apps.story.models import Shot, ShotTake

        from apps.production.models import Asset

        persist_bible(self.project, {
            "characters": [{"id": "amina", "name": "Amina", "look": "visage canonique"}],
            "locations": [{"id": "cuisine", "name": "Cuisine", "look": "cuisine canonique"}],
            "props": [],
        })
        Asset.objects.create(
            project=self.project,
            kind=Asset.Kind.IMAGE,
            role=Asset.Role.CHARACTER_REF,
            uri="/media/refs/amina.png",
            meta={"key": "amina"},
        )
        Asset.objects.create(
            project=self.project,
            kind=Asset.Kind.IMAGE,
            role=Asset.Role.LOCATION_REF,
            uri="/media/refs/cuisine.png",
            meta={"key": "cuisine"},
        )
        beat = persist_beats(self.episode, [{
            "text": "Amina reste assise et regarde la tasse.",
            "character_ids": ["amina"],
            "location_id": "cuisine",
            "scene_index": 1,
            "duration_seconds": 8,
            "video_prompt": "Amina remains seated, looking at the cup.",
        }])[0]
        shot = Shot.objects.create(
            beat=beat,
            index=1,
            text="Amina reste assise et regarde la tasse.",
            duration_seconds=8,
            video_prompt="Amina remains seated, looking at the cup.",
        )
        ShotTake.objects.create(
            shot=shot,
            number=1,
            uri="/media/clips/previous.mp4",
            status=ShotTake.Status.REVIEW,
        )

        class FakeVideo:
            provider_id = "fake-veo"

            def extract_reference_frame(self, uri, *, project_key=None):
                self.previous_uri = uri
                return "/media/take-frames/previous.jpg"

            def render(self, prompt, **kwargs):
                self.prompt = prompt
                self.kwargs = kwargs
                return "/media/clips/adjusted.mp4"

        backend = FakeVideo()
        with patch("agents.backends.get_video", return_value=backend):
            render_shot(shot, adjustment_prompt="caméra plus proche")

        take = shot.takes.order_by("-number").first()
        self.assertEqual(backend.previous_uri, "/media/clips/previous.mp4")
        self.assertEqual(backend.kwargs["start_frame"], "/media/take-frames/previous.jpg")
        self.assertEqual(backend.kwargs["ingredients"], [])
        self.assertEqual(take.generation_meta["previous_take_frame"], "/media/take-frames/previous.jpg")
        self.assertIn("caméra plus proche", take.prompt)

    def test_shot_review_locks_exact_take(self):
        beat = persist_beats(self.episode, [{"text": "Beat narratif", "duration_seconds": 12}])[0]
        shot = plan_beat_shots(beat)[0]
        first = ShotTake.objects.create(shot=shot, number=1, uri="file:///tmp/shot-one.mp4", status=ShotTake.Status.REVIEW)
        second = ShotTake.objects.create(shot=shot, number=2, uri="file:///tmp/shot-two.mp4", status=ShotTake.Status.REVIEW)
        review_shot(shot, "approve", take_id=second.id)
        first.refresh_from_db(); second.refresh_from_db(); shot.refresh_from_db()
        self.assertEqual(second.status, ShotTake.Status.LOCKED)
        self.assertEqual(first.status, ShotTake.Status.REVIEW)
        self.assertEqual(shot.status, Beat.Status.LOCKED)

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

    def test_assembly_requires_locked_take_for_every_latest_shot(self):
        beats = persist_beats(self.episode, [{"text": "Un"}, {"text": "Deux"}])
        shots = [plan_beat_shots(beat)[0] for beat in beats]
        ShotTake.objects.create(shot=shots[0], number=1, uri="file:///tmp/one.mp4", status=ShotTake.Status.LOCKED)

        with self.assertRaisesMessage(ValueError, "aucun take verrouillé"):
            assemble_episode(self.episode)

    def test_assembly_uses_locked_shot_takes_in_story_order(self):
        beats = persist_beats(self.episode, [{"text": "Un"}, {"text": "Deux"}])
        shots = [plan_beat_shots(beat)[0] for beat in beats]
        with TemporaryDirectory() as tmp:
            for i, shot in enumerate(shots):
                path = Path(tmp) / f"{i}.mp4"
                path.write_bytes(b"fake")
                ShotTake.objects.create(
                    shot=shot,
                    number=1,
                    uri=path.as_uri(),
                    status=ShotTake.Status.LOCKED,
                )

            media = Path(tmp) / "media"
            with patch.dict("os.environ", {"STUDIO_MEDIA_ROOT": str(media)}), patch("apps.projects.assembly.subprocess.run") as run:
                asset = assemble_episode(self.episode)

            run.assert_called_once()
            manifest = run.call_args.args[0]
            self.assertEqual(manifest[0], "ffmpeg")
            self.assertEqual(asset.role, "episode_cut")
            self.assertEqual([row["beat_id"] for row in asset.meta["shots"]], [b.id for b in beats])
            self.assertEqual([row["shot_id"] for row in asset.meta["shots"]], [s.id for s in shots])

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

    def test_conversation_segmentation_sets_canonical_speaker_id(self):
        persist_bible(self.project, {
            "characters": [{
                "id": "antoine-kasongo",
                "name": "Antoine Kasongo",
                "aliases": ["Antoine"],
                "role": "protagoniste",
            }],
            "locations": [],
            "props": [],
        })
        chunks = [{
            "text": "Antoine Kasongo : Je vais ouvrir cet atelier et terminer enfin le travail que mon grand-pere avait commence avant son depart.",
            "dialogue": "Antoine : Je vais ouvrir cet atelier.",
            "character_ids": ["antoine-kasongo"],
        }]
        errors = _segmentation_errors(chunks, form="conversation", project=self.project)
        self.assertEqual(errors, [])
        self.assertEqual(chunks[0]["speaker_id"], "antoine-kasongo")

    def test_continuity_context_uses_canonical_entities_and_speaker(self):
        persist_bible(self.project, {
            "characters": [{
                "id": "antoine",
                "name": "Antoine",
                "role": "artisan",
                "look": "chemise blanche, cheveux courts",
                "voice": "calme",
            }],
            "locations": [{
                "id": "atelier",
                "name": "Atelier",
                "look": "etablis en bois et murs patines",
                "time_of_day": "jour",
            }],
            "props": [{
                "id": "carnet",
                "name": "Carnet",
                "look": "cuir brun use",
                "story_function": "heritage",
            }],
        })
        character = Character.objects.get(project=self.project)
        location = Location.objects.get(project=self.project)
        prop = Prop.objects.get(project=self.project)
        beat = persist_beats(self.episode, [{
            "text": "Antoine ouvre le carnet sur l'etabli et observe les dessins avant de reprendre lentement son travail.",
            "scene_index": 1,
            "scene_heading": "INT. ATELIER - JOUR",
            "location_id": "atelier",
            "character_ids": ["antoine"],
            "speaker_id": "antoine",
            "prop_ids": ["carnet"],
            "dialogue": "Antoine : Je vais finir ce travail.",
            "continuity": {"wardrobe": "chemise blanche"},
        }])[0]

        context = build_continuity_context(beat)
        prompt = continuity_prompt(beat, context)

        self.assertEqual(context["speaker"]["key"], character.key)
        self.assertEqual(context["location"]["key"], location.key)
        self.assertEqual(context["props"][0]["key"], prop.key)
        self.assertTrue(context["characters"][0]["is_speaker"])
        self.assertIn("chemise blanche", prompt)
        self.assertIn("Atelier", prompt)
        self.assertIn("Carnet", prompt)

    def test_script_speaker_is_promoted_to_locked_bible(self):
        bible = persist_bible(self.project, {
            "characters": [{
                "id": "leo-dubois",
                "name": "Léo Dubois",
                "aliases": ["Dr. Léo Dubois"],
                "role": "scientifique",
                "look": "scientifique",
            }],
            "locations": [],
            "props": [],
        })
        bible.locked = True
        bible.save(update_fields=["locked"])

        _ensure_script_speakers(
            self.project,
            bible,
            "CLAIRE MOREAU : On descend.\nDR. LÉO DUBOIS : Continuez.",
        )

        resolver = CharacterResolver(self.project)
        self.assertEqual(resolver.resolve("DR. LÉO DUBOIS").key, "leo-dubois")
        claire = resolver.resolve("CLAIRE MOREAU")
        self.assertIsNotNone(claire)
        self.assertEqual(claire.key, "claire-moreau")
        self.assertTrue(Character.objects.get(project=self.project, key="claire-moreau").locked)

    def test_script_speaker_parser_rejects_metadata_and_prose_labels(self):
        labels = _script_speaker_labels(
            "Title: Le silence des abysses\n"
            "Author: Studio\n"
            "Episode: 3\n"
            "C'est la première phase, Claire : les charognards arrivent.\n"
            "CLAIRE_MOREAU: Des mondes invisibles ?\n"
            "LEO_DUBOIS: Exactement."
        )
        self.assertEqual(labels, ["CLAIRE_MOREAU", "LEO_DUBOIS"])

    def test_cleanup_removes_only_known_bogus_generated_speakers(self):
        bible = persist_bible(self.project, {
            "characters": [
                {"id": "title", "name": "Title", "role": "interlocuteur"},
                {"id": "claire-moreau", "name": "Claire Moreau", "role": "interlocuteur"},
            ],
            "locations": [],
            "props": [],
        })
        bible.locked = True
        bible.save(update_fields=["locked"])
        cleanup_generated_script_characters(self.project)
        self.assertFalse(Character.objects.filter(project=self.project, name="Title").exists())
        self.assertTrue(Character.objects.filter(project=self.project, name="Claire Moreau").exists())

    def test_normalizer_splits_two_speakers_into_distinct_beats(self):
        self.project.delivery = "conversation"
        self.project.save(update_fields=["delivery"])
        persist_bible(self.project, {
            "characters": [
                {"id": "claire-moreau", "name": "Claire Moreau", "aliases": ["CLAIRE MOREAU"]},
                {"id": "leo-dubois", "name": "Léo Dubois", "aliases": ["LEO DUBOIS"]},
            ],
            "locations": [], "props": [],
        })
        resolver = CharacterResolver(self.project)
        rows = normalize_beats([{
            "text": "CLAIRE MOREAU : Une victoire silencieuse, loin des regards. LEO DUBOIS : Exactement, Claire. La quête continue dans les profondeurs.",
            "dialogue": "CLAIRE MOREAU : Une victoire silencieuse, loin des regards. LEO DUBOIS : Exactement, Claire. La quête continue dans les profondeurs.",
            "character_ids": ["claire-moreau", "leo-dubois"],
            "scene_index": 1,
        }], form="conversation", resolve_character_names=resolver.names_for_row)

        self.assertEqual(len(rows), 2)
        self.assertIn("CLAIRE MOREAU", rows[0]["text"])
        self.assertNotIn("LEO DUBOIS", rows[0]["text"])
        self.assertIn("LEO DUBOIS", rows[1]["text"])
        self.assertEqual(_segmentation_errors(rows, form="conversation", project=self.project), [])
        self.assertEqual(rows[0]["speaker_id"], "claire-moreau")
        self.assertEqual(rows[1]["speaker_id"], "leo-dubois")

    def test_normalizer_does_not_merge_short_dialogue_across_speakers(self):
        rows = normalize_beats([
            {"text": "CLAIRE MOREAU : Des mondes invisibles ?", "dialogue": "CLAIRE MOREAU : Des mondes invisibles ?", "scene_index": 1},
            {"text": "LEO DUBOIS : Exactement, Claire.", "dialogue": "LEO DUBOIS : Exactement, Claire.", "scene_index": 1},
        ], form="conversation", resolve_character_names=lambda row: [])
        self.assertEqual(len(rows), 2)
        self.assertTrue(rows[0]["text"].startswith("CLAIRE MOREAU"))
        self.assertTrue(rows[1]["text"].startswith("LEO DUBOIS"))

    def test_long_single_sentence_dialogue_is_not_cut_mid_sentence(self):
        source = "CLAIRE MOREAU : " + " ".join(f"mot{i}" for i in range(70))
        rows = normalize_beats([{
            "text": source,
            "dialogue": source,
            "scene_index": 1,
        }], form="conversation", resolve_character_names=lambda row: ["Claire Moreau"])

        # A single oversized sentence stays intact so the semantic repair pass
        # can rewrite it naturally instead of producing broken dialogue clips.
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["text"], source)
        self.assertEqual(rows[0]["dialogue"], source)
        self.assertGreater(len(rows[0]["text"].split()), 32)

    def test_long_multi_sentence_dialogue_splits_only_on_sentence_boundaries(self):
        source = (
            "CLAIRE MOREAU : " + " ".join(f"a{i}" for i in range(18)) + ". "
            + " ".join(f"b{i}" for i in range(18)) + ". "
            + " ".join(f"c{i}" for i in range(18)) + "."
        )
        rows = normalize_beats([{
            "text": source,
            "dialogue": source,
            "scene_index": 1,
        }], form="conversation", resolve_character_names=lambda row: ["Claire Moreau"])

        self.assertGreater(len(rows), 1)
        self.assertTrue(all(row["text"].endswith(".") for row in rows))
        self.assertTrue(all(len(row["text"].split()) <= 32 for row in rows))

    def test_orphan_dialogue_fragment_inherits_previous_speaker(self):
        self.project.delivery = "conversation"
        self.project.save(update_fields=["delivery"])
        persist_bible(self.project, {
            "characters": [{"id": "chloe", "name": "Chloé", "aliases": ["CHLOÉ"]}],
            "locations": [], "props": [],
        })
        resolver = CharacterResolver(self.project)
        rows = normalize_beats([
            {
                "text": "CHLOÉ : Elle prend la tasse. Merci d'être là.",
                "dialogue": "CHLOÉ : Merci d'être là.",
                "character_ids": ["chloe"],
                "scene_index": 1,
            },
            {
                "text": "Tu as probablement raison...",
                "character_ids": ["chloe"],
                "scene_index": 1,
            },
        ], form="conversation", resolve_character_names=resolver.names_for_row)

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1]["speaker_id"], "chloe")
        self.assertTrue(rows[1]["dialogue"].startswith("CHLOÉ"))
        self.assertTrue(rows[1]["speaker_inherited"])

    def test_shot_package_freezes_reference_uids_and_reuses_them_for_adjustment(self):
        from apps.projects.continuity import shot_render_package
        from apps.production.models import Asset
        from apps.story.models import Shot, ShotTake

        persist_bible(self.project, {
            "characters": [{"id": "chloe", "name": "Chloé", "look": "visage canonique"}],
            "locations": [{"id": "cuisine", "name": "Cuisine", "look": "cuisine canonique"}],
            "props": [],
        })
        character = self.project.characters.get(key="chloe")
        location = self.project.locations.get(key="cuisine")
        Asset.objects.create(project=self.project, kind=Asset.Kind.IMAGE, role=Asset.Role.CHARACTER_REF, uri="/tmp/chloe.png", meta={"key": "chloe"})
        Asset.objects.create(project=self.project, kind=Asset.Kind.IMAGE, role=Asset.Role.LOCATION_REF, uri="/tmp/cuisine.png", meta={"key": "cuisine"})
        beat = persist_beats(self.episode, [{
            "text": "Chloé parle dans la cuisine.",
            "dialogue": "CHLOÉ : Bonjour.",
            "speaker_id": "chloe",
            "character_ids": ["chloe"],
            "location_id": "cuisine",
            "scene_index": 1,
            "video_prompt": "Plan rapproché de Chloé.",
        }])[0]
        shot = Shot.objects.create(beat=beat, index=1, text=beat.text, duration_seconds=6, video_prompt=beat.video_prompt)
        first = shot_render_package(shot)
        shot.refresh_from_db()
        self.assertEqual(shot.reference_uids, [character.reference_uid, location.reference_uid])
        ShotTake.objects.create(shot=shot, number=1, uri="/tmp/take1.mp4", status=ShotTake.Status.REVIEW)
        adjusted = shot_render_package(shot, adjustment_prompt="Cadre plus serré")
        self.assertEqual([item["reference_uid"] for item in adjusted["ingredients"]["items"]], shot.reference_uids)
        self.assertEqual(adjusted["previous_take"]["number"], 1)
        self.assertIn("LANGUAGE LOCK", adjusted["prompt"])
        self.assertIn("PREVIOUS TAKE CONTINUITY", adjusted["prompt"])

    def test_video_media_refs_prioritize_speaker_then_characters_then_location(self):
        from apps.projects.continuity import resolve_ingredients
        from apps.production.models import Asset

        persist_bible(self.project, {
            "characters": [
                {"id": "alice", "name": "Alice", "look": "look Alice"},
                {"id": "bob", "name": "Bob", "look": "look Bob"},
            ],
            "locations": [{"id": "salon", "name": "Salon", "look": "salon canonique"}],
            "props": [{"id": "telephone", "name": "Téléphone", "look": "téléphone noir"}],
        })
        for role, key in [
            (Asset.Role.CHARACTER_REF, "alice"),
            (Asset.Role.CHARACTER_REF, "bob"),
            (Asset.Role.LOCATION_REF, "salon"),
            (Asset.Role.PROP_REF, "telephone"),
        ]:
            Asset.objects.create(project=self.project, kind=Asset.Kind.IMAGE, role=role, uri=f"/tmp/{key}.png", meta={"key": key})
        beat = persist_beats(self.episode, [{
            "text": "Bob parle à Alice dans le salon.",
            "dialogue": "BOB : Bonjour Alice.",
            "speaker_id": "bob",
            "character_ids": ["alice", "bob"],
            "location_id": "salon",
            "prop_ids": ["telephone"],
            "scene_index": 1,
            "video_prompt": "Bob parle à Alice.",
        }])[0]

        pack = resolve_ingredients(beat)
        self.assertEqual(
            [item["key"] for item in pack["media_items"]],
            ["bob", "alice", "salon", "telephone"],
        )
        self.assertEqual(pack["uris"][:3], ["/tmp/bob.png", "/tmp/alice.png", "/tmp/salon.png"])
        self.assertEqual(len(pack["items"]), 4)

    def test_render_readiness_blocks_missing_visual_refs(self):
        persist_bible(self.project, {
            "characters": [{"id": "chloe", "name": "Chloé", "look": "pyjama confortable"}],
            "locations": [{"id": "cuisine", "name": "Cuisine", "look": "lumière tamisée"}],
            "props": [],
        })
        beat = persist_beats(self.episode, [{
            "text": "CHLOÉ : Impossible de fermer l'œil.",
            "dialogue": "CHLOÉ : Impossible de fermer l'œil.",
            "speaker_id": "chloe",
            "character_ids": ["chloe"],
            "location_id": "cuisine",
            "scene_index": 1,
            "video_prompt": "Plan rapproché de Chloé dans la cuisine.",
        }])[0]

        readiness = validate_render_readiness(beat)
        self.assertFalse(readiness["ready"])
        self.assertTrue(any("chloe" in error for error in readiness["errors"]))
        self.assertTrue(any("cuisine" in error for error in readiness["errors"]))

    def test_persist_beats_bounds_compact_generated_fields(self):
        long_value = "x" * 500
        beat = persist_beats(self.episode, [{
            "text": "Une action visuelle simple pour tester les limites de stockage du beat.",
            "scene_index": 1,
            "scene_heading": long_value,
            "time_of_day": long_value,
            "emotion": long_value,
            "backend": long_value,
        }])[0]
        beat.refresh_from_db()
        self.assertEqual(len(beat.emotion), Beat._meta.get_field("emotion").max_length)
        self.assertEqual(len(beat.backend), Beat._meta.get_field("backend").max_length)
        self.assertEqual(len(beat.scene.heading), Scene._meta.get_field("heading").max_length)
        self.assertEqual(len(beat.scene.time_of_day), Scene._meta.get_field("time_of_day").max_length)

    def test_scene_contract_rejects_location_change_without_new_scene(self):
        persist_bible(self.project, {"characters": [], "locations": [
            {"id": "maison", "name": "Maison", "look": "interieur"},
            {"id": "route", "name": "Route", "look": "rue"},
        ], "props": []})
        with self.assertRaisesMessage(ValueError, "changement de lieu"):
            persist_beats(self.episode, [
                {"text": "Le personnage quitte la maison.", "scene_index": 1, "location_id": "maison"},
                {"text": "Le personnage marche dans la rue.", "scene_index": 1, "location_id": "route"},
            ])

    def test_scene_contract_accepts_location_change_with_new_scene(self):
        persist_bible(self.project, {"characters": [], "locations": [
            {"id": "maison", "name": "Maison", "look": "interieur"},
            {"id": "route", "name": "Route", "look": "rue"},
        ], "props": []})
        beats = persist_beats(self.episode, [
            {"text": "Le personnage quitte la maison.", "scene_index": 1, "location_id": "maison"},
            {"text": "Le personnage marche dans la rue.", "scene_index": 2, "location_id": "route"},
        ])
        self.assertEqual(len(beats), 2)
        self.assertNotEqual(beats[0].scene_id, beats[1].scene_id)

    def test_redundancy_validator_rejects_near_duplicate_beats_for_same_event(self):
        from apps.projects.services import _event_redundancy_errors

        errors = _event_redundancy_errors([
            {"event_id": "EV05", "text": "Leo salue joyeusement les passants sur le chemin de l'ecole."},
            {"event_id": "EV05", "text": "Leo salue joyeusement les passants sur le chemin vers l'ecole."},
        ])
        self.assertTrue(errors)
        self.assertIn("EV05", errors[0])

    def test_redundancy_validator_allows_distinct_visual_steps_for_same_event(self):
        from apps.projects.services import _event_redundancy_errors

        errors = _event_redundancy_errors([
            {"event_id": "EV05", "text": "Leo leve la main vers une voisine devant sa maison."},
            {"event_id": "EV05", "text": "Le boulanger sourit et repond au salut de Leo depuis sa boutique."},
        ])
        self.assertEqual(errors, [])


    def test_project_constraints_payload_exposes_canonical_story_format(self):
        from apps.projects.services import project_constraints_payload

        self.project.genre = "Drame familial"
        self.project.subgenre = "Mystère"
        self.project.setting = "Kinshasa, RDC"
        self.project.episode_count_target = 5
        self.project.episode_duration_seconds = 60
        self.project.delivery = "voix_off"
        self.project.visual_style = "realistic"
        self.project.save()

        payload = project_constraints_payload(self.project)
        self.assertEqual(payload["genre"], "Drame familial")
        self.assertEqual(payload["subgenre"], "Mystère")
        self.assertEqual(payload["setting"], "Kinshasa, RDC")
        self.assertEqual(payload["episode_count_target"], 5)
        self.assertEqual(payload["episode_duration_seconds"], 60)
        self.assertEqual(payload["delivery"], "voix_off")
        self.assertEqual(payload["visual_style"], "realistic")


    def test_scene_plan_rejects_unknown_location_and_missing_event(self):
        from apps.projects.services import _scene_plan_errors

        persist_bible(self.project, {
            "characters": [{"id": "leo", "name": "Leo"}],
            "locations": [{"id": "maison", "name": "Maison", "look": "interieur"}],
            "props": [],
        })
        errors = _scene_plan_errors(
            [{"index": 1, "location_id": "route", "time_of_day": "matin", "character_ids": ["leo"], "prop_ids": [], "event_ids": ["EV01"], "target_seconds": 60}],
            project=self.project,
            episode=self.episode,
            expected_events={"EV01", "EV02"},
        )
        self.assertTrue(any("location_id canonique invalide" in error for error in errors))
        self.assertTrue(any("EV02" in error for error in errors))

    def test_beat_scene_plan_rejects_scene_drift(self):
        from apps.projects.services import _beat_scene_plan_errors

        errors = _beat_scene_plan_errors(
            [{"scene_index": 1, "location_id": "ecole", "time_of_day": "matin", "event_id": "EV01"}],
            [{"index": 1, "location_id": "maison", "time_of_day": "matin", "event_ids": ["EV01"]}],
        )
        self.assertTrue(any("location_id" in error for error in errors))

    def test_beat_scene_plan_accepts_locked_scene_contract(self):
        from apps.projects.services import _beat_scene_plan_errors

        errors = _beat_scene_plan_errors(
            [{"scene_index": 2, "location_id": "route", "time_of_day": "matin", "event_id": "EV04"}],
            [{"index": 2, "location_id": "route", "time_of_day": "matin", "event_ids": ["EV04", "EV05"]}],
        )
        self.assertEqual(errors, [])


    def test_lock_scene_plan_keeps_only_one_locked_version(self):
        from apps.story.models import ScenePlan, Script
        from apps.projects.models import NarrativeContract, NarrativeEvent
        from apps.projects.services import lock_scene_plan, persist_bible

        bible = persist_bible(self.project, {
            "characters": [{"id": "leo", "name": "Leo"}],
            "locations": [{"id": "maison", "name": "Maison", "look": "interieur"}],
            "props": [],
        })
        bible.locked = True
        bible.save(update_fields=["locked"])
        contract = NarrativeContract.objects.create(project=self.project)
        NarrativeEvent.objects.create(contract=contract, key="EV01", position=1, description="Leo se prepare", episode_number=self.episode.number)
        script = Script.objects.create(episode=self.episode, version=1, fountain="INT. MAISON - MATIN")
        payload = [{"index": 1, "heading": "INT. MAISON - MATIN", "summary": "Leo se prepare", "location_id": "maison", "time_of_day": "matin", "character_ids": ["leo"], "prop_ids": [], "event_ids": ["EV01"], "target_seconds": 60}]
        first = ScenePlan.objects.create(episode=self.episode, script=script, version=1, payload=payload, locked=True)
        second = ScenePlan.objects.create(episode=self.episode, script=script, version=2, payload=payload)

        locked = lock_scene_plan(self.episode, second.id)
        first.refresh_from_db()
        self.assertTrue(locked.locked)
        self.assertFalse(first.locked)


    @patch("agents.roles.showrunner.Showrunner.plan")
    def test_showrunner_creates_missing_narrative_contract_and_episode_events(self, mock_plan):
        from apps.projects.services import run_showrunner

        mock_plan.return_value = {
            "tone": "intime",
            "episodes": [{
                "number": 1,
                "title": "Le cafe de minuit",
                "logline": "Deux colocataires parlent dans la cuisine.",
                "function_in_arc": "resolution",
                "events": ["Mani doute de son avenir.", "Nathalie lui offre une boisson chaude."],
            }],
            "checkpoints": [],
        }
        self.assertFalse(NarrativeContract.objects.filter(project=self.project).exists())
        run_showrunner(self.project)
        contract = NarrativeContract.objects.get(project=self.project)
        self.assertTrue(contract.locked)
        self.assertEqual(
            list(contract.events.values_list("key", "episode_number")),
            [("EV01", 1), ("EV02", 1)],
        )


    def test_persist_beats_on_locked_plan_keeps_script_and_creates_segmentation_version(self):
        from apps.story.models import ScenePlan, Segmentation
        from apps.projects.services import persist_beats
        script = Script.objects.create(episode=self.episode, version=1, fountain="Script canonique")
        plan = ScenePlan.objects.create(episode=self.episode, script=script, version=1, locked=True, payload=[{"index": 1, "target_seconds": 8}])
        before_scripts = self.episode.scripts.count()
        beats = persist_beats(self.episode, [{"text": "Action distincte.", "scene_index": 1, "duration_seconds": 8}], script=script, scene_plan=plan)
        self.assertEqual(self.episode.scripts.count(), before_scripts)
        self.assertEqual(Segmentation.objects.filter(script=script).count(), 1)
        self.assertEqual(beats[0].script_id, script.id)
        self.assertIsNotNone(beats[0].segmentation_id)

    def test_auto_duration_constraints_expose_null_target(self):
        from apps.projects.services import project_constraints_payload
        self.project.episode_duration_seconds = None
        self.project.save(update_fields=["episode_duration_seconds"])
        self.assertIsNone(project_constraints_payload(self.project)["episode_duration_seconds"])

    def test_fixed_duration_budget_is_stricter_per_episode(self):
        from apps.projects.services import _duration_budget_errors
        scene_plan = [{"index": 1, "target_seconds": 60}]
        chunks = [{"scene_index": 1, "duration_seconds": 71}]
        self.assertTrue(_duration_budget_errors(chunks, scene_plan, fixed_episode_target=60))
        self.assertFalse(_duration_budget_errors(
            [{"scene_index": 1, "duration_seconds": 65}],
            scene_plan,
            fixed_episode_target=60,
        ))

    def test_duration_budget_rejects_scene_far_over_target(self):
        from apps.projects.services import _duration_budget_errors
        errors = _duration_budget_errors(
            [{"scene_index": 1, "duration_seconds": 8}, {"scene_index": 1, "duration_seconds": 8}, {"scene_index": 1, "duration_seconds": 8}],
            [{"index": 1, "target_seconds": 10}],
        )
        self.assertTrue(errors)
        self.assertIn("cible de 10s", errors[0])


    def test_persist_beats_rolls_back_entire_segmentation_on_failure(self):
        before_scripts = Script.objects.filter(episode=self.episode).count()
        before_beats = Beat.objects.filter(episode=self.episode).count()
        before_scenes = self.episode.scenes.count()
        original_create = Beat.objects.create
        calls = {"count": 0}

        def fail_on_second_beat(*args, **kwargs):
            calls["count"] += 1
            if calls["count"] == 2:
                raise RuntimeError("simulated persistence failure")
            return original_create(*args, **kwargs)

        with patch.object(Beat.objects, "create", side_effect=fail_on_second_beat):
            with self.assertRaisesMessage(RuntimeError, "simulated persistence failure"):
                persist_beats(self.episode, [
                    {"text": "Premier beat valide", "scene_index": 1},
                    {"text": "Deuxieme beat qui echoue", "scene_index": 2},
                ])

        self.assertEqual(Script.objects.filter(episode=self.episode).count(), before_scripts)
        self.assertEqual(Beat.objects.filter(episode=self.episode).count(), before_beats)
        self.assertEqual(self.episode.scenes.count(), before_scenes)


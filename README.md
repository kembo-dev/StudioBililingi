# StudioBililingi

Studio de production de séries IA.

Un concept d’histoire devient une bible (personnages, lieux, objets), des épisodes, des scripts, puis des **beats d’environ 24 mots** destinés à la génération vidéo. Rien ne passe à l’étape suivante sans validation humaine.

Ce n’est pas un générateur de clips. C’est le système de production au-dessus des générateurs.

## Stack

| Couche | Techno |
|---|---|
| UI | Next.js + Tailwind |
| API / métier | Django |
| Agents | Google ADK — rôles stables, backends interchangeables |
| Défaut génération | Gemini, Nano Banana, Veo 3.1 / Omni Flash, Lyria |
| Données | PostgreSQL + Redis |

## Monorepo

```
backend/              Django (source de vérité)
web/                  Next.js (studio)
agents/               rôles ADK + protocoles Text/Image/Video/Audio
packages/shared/      contrats JSON (bible, épisode, beat)
```

## Principes

1. **Rôles ≠ vendors.** Un Beat Segmenter reste un Beat Segmenter. Veo ou Seedance passent par `VideoBackend`.
2. **Le Beat est l’atome.** ~24 mots, 6–8 s, refs visuelles, prompt, clip, revue.
3. **HITL obligatoire** après bible, planches, storyboard, et chaque épisode.
4. **Versions partout.** Bible v3, beat 12 take 4.

## Démarrage local

```bash
cp .env.example .env
docker compose up --build
```

- API : http://localhost:8000/api/health/
- Studio : http://localhost:3000

## Licence

MIT.

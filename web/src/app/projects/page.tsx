"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import { api } from "@/lib/api";

type Project = { id: number; title: string; slug: string; concept: string; status: string };
type ConceptSuggestion = {
  title: string; concept: string; genre: string; tone: string; story_type: string;
  recommended_episode_count: number; events: string[]; ending_intent: string;
};

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [title, setTitle] = useState("");
  const [concept, setConcept] = useState("");
  const [delivery, setDelivery] = useState("storytell");
  const [visualStyle, setVisualStyle] = useState("realistic");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [conceptMode, setConceptMode] = useState<"manual" | "ai">("manual");
  const [idea, setIdea] = useState("");
  const [assistBusy, setAssistBusy] = useState(false);
  const [suggestion, setSuggestion] = useState<ConceptSuggestion | null>(null);
  const [genre, setGenre] = useState("");
  const [tone, setTone] = useState("");
  const [endingIntent, setEndingIntent] = useState("");

  async function load() {
    setProjects(await api<Project[]>("/api/projects/"));
  }

  useEffect(() => {
    load().catch((err) => setError(String(err)));
  }, []);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const project = await api<Project>("/api/projects/", {
        method: "POST",
        body: JSON.stringify({ title, concept, genre, tone, ending_intent: endingIntent, delivery, visual_style: visualStyle }),
      });
      window.location.href = `/projects/${project.id}`;
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-8 px-6 py-12">
      <p className="text-sm tracking-[0.2em] text-[#e8c36a] uppercase">
        <Link href="/">StudioBililingi</Link>
      </p>
      <h1 className="text-3xl font-semibold">Projets</h1>
      <form onSubmit={onSubmit} className="space-y-3 rounded-xl border border-[#2a2e38] bg-[#14161c] p-4">
        <label className="block text-xs text-[#9aa3b2]">
          Titre
          <input className="mt-1 w-full rounded-lg border border-[#2a2e38] bg-[#0b0c10] px-3 py-2 text-sm text-white outline-none" placeholder="L’Appel de 03h14" value={title} onChange={(e) => setTitle(e.target.value)} required />
        </label>
        <div>
          <p className="mb-2 text-sm font-medium text-[#e8c36a]">Création du concept</p>
          <div className="grid grid-cols-2 gap-2">
            <button type="button" onClick={() => setConceptMode("manual")} className={conceptMode === "manual" ? "rounded-lg bg-[#e8c36a] px-3 py-2 text-sm font-medium text-[#0b0c10]" : "rounded-lg border border-[#2a2e38] px-3 py-2 text-sm text-[#9aa3b2]"}>Écrire moi-même</button>
            <button type="button" onClick={() => setConceptMode("ai")} className={conceptMode === "ai" ? "rounded-lg bg-[#e8c36a] px-3 py-2 text-sm font-medium text-[#0b0c10]" : "rounded-lg border border-[#2a2e38] px-3 py-2 text-sm text-[#9aa3b2]"}>✨ M'aider avec l'IA</button>
          </div>
        </div>
        {conceptMode === "ai" ? (
          <div className="space-y-3 rounded-xl border border-[#2a2e38] bg-[#0b0c10] p-4">
            <label className="block text-xs text-[#9aa3b2]">
              Ton idée de départ
              <textarea className="mt-1 min-h-24 w-full rounded-lg border border-[#2a2e38] bg-[#14161c] px-3 py-2 text-sm text-white outline-none" placeholder="Ex. Un enfant joyeux se prépare, marche vers l'école et salue les personnes qu'il rencontre." value={idea} onChange={(e) => setIdea(e.target.value)} />
            </label>
            <button type="button" disabled={assistBusy || !idea.trim()} onClick={async () => {
              setAssistBusy(true); setError("");
              try {
                const result = await api<ConceptSuggestion>("/api/projects/assist-concept/", { method: "POST", body: JSON.stringify({ idea, delivery }) });
                setSuggestion(result);
              } catch (err) { setError(String(err)); } finally { setAssistBusy(false); }
            }} className="rounded-lg border border-[#e8c36a] px-4 py-2 text-sm text-[#e8c36a] disabled:opacity-50">
              {assistBusy ? "Analyse de l'idée…" : suggestion ? "✨ Proposer une autre version" : "✨ Développer avec l'IA"}
            </button>
            {suggestion ? (
              <div className="space-y-3 rounded-lg border border-[#2a2e38] bg-[#14161c] p-4 text-sm">
                <div className="flex items-start justify-between gap-3"><div><p className="font-medium">{suggestion.title || "Proposition"}</p><p className="text-xs text-[#9aa3b2]">{suggestion.genre || "Genre libre"} · {suggestion.tone || "Ton libre"} · {suggestion.recommended_episode_count} épisode(s) recommandé(s)</p></div><span className="rounded-full border border-[#2a2e38] px-2 py-1 text-[10px] uppercase text-[#9aa3b2]">{suggestion.story_type || "story"}</span></div>
                <p className="text-[#d7dbe3]">{suggestion.concept}</p>
                {suggestion.events.length ? <ol className="list-decimal space-y-1 pl-5 text-xs text-[#9aa3b2]">{suggestion.events.map((event, index) => <li key={index}>{event}</li>)}</ol> : null}
                <button type="button" onClick={() => {
                  setTitle(suggestion.title || title); setConcept(suggestion.concept);
                  setGenre(suggestion.genre); setTone(suggestion.tone); setEndingIntent(suggestion.ending_intent);
                }} className="rounded-lg bg-[#e8c36a] px-4 py-2 text-sm font-medium text-[#0b0c10]">✓ Utiliser ce concept</button>
              </div>
            ) : null}
          </div>
        ) : null}
        <label className="block text-xs text-[#9aa3b2]">
          Concept {conceptMode === "ai" ? "retenu (modifiable)" : ""}
          <textarea className="mt-1 min-h-28 w-full rounded-lg border border-[#2a2e38] bg-[#0b0c10] px-3 py-2 text-sm text-white outline-none" placeholder="Genre / Concept / Début / Fin" value={concept} onChange={(e) => setConcept(e.target.value)} required />
        </label>
        <div>
          <p className="mb-2 text-sm font-medium text-[#e8c36a]">Type de rendu</p>
          <div className="grid grid-cols-2 gap-2">
            {[
              ["storytell", "Storytell"],
              ["voix_off", "Voix off"],
              ["conversation", "Conversation"],
              ["rencontre", "Rencontre"],
            ].map(([value, label]) => (
              <button key={value} type="button" onClick={() => setDelivery(value)} className={delivery === value ? "rounded-lg bg-[#e8c36a] px-3 py-2 text-sm font-medium text-[#0b0c10]" : "rounded-lg border border-[#2a2e38] px-3 py-2 text-sm text-[#9aa3b2]"}>
                {label}
              </button>
            ))}
          </div>
        </div>
        <label className="block text-xs text-[#9aa3b2]">
          Style visuel de production
          <select
            value={visualStyle}
            onChange={(e) => setVisualStyle(e.target.value)}
            className="mt-1 w-full rounded-lg border border-[#2a2e38] bg-[#0b0c10] px-3 py-2 text-sm text-white outline-none"
          >
            <option value="realistic">Réaliste cinématographique</option>
            <option value="realistic_imperfect">Réaliste avec imperfections réelles</option>
            <option value="cartoon">Cartoon 2D</option>
            <option value="manga">Manga / Anime</option>
            <option value="3d_animation">Animation 3D</option>
            <option value="comic">Bande dessinée / Comic</option>
            <option value="watercolor">Aquarelle</option>
            <option value="claymation">Claymation / Stop-motion</option>
            <option value="pixel_art">Pixel art</option>
            <option value="film_noir">Film noir</option>
            <option value="fantasy">Fantasy stylisée</option>
          </select>
          <span className="mt-1 block text-[11px]">Ce choix verrouille les personnages, lieux, objets et rendus vidéo du projet.</span>
        </label>
        <button disabled={busy} className="rounded-lg bg-[#e8c36a] px-4 py-2 text-sm font-medium text-[#0b0c10] disabled:opacity-50">
          {busy ? "Création…" : "Créer + bible + saison"}
        </button>
        {error ? <p className="text-sm text-red-400">{error}</p> : null}
      </form>
      <ul className="space-y-2">
        {projects.map((project) => (
          <li key={project.id} className="flex items-start gap-2 rounded-xl border border-[#2a2e38] bg-[#14161c] px-4 py-3">
            <Link href={`/projects/${project.id}`} className="min-w-0 flex-1">
              <p className="font-medium">{project.title}</p>
              <p className="text-sm text-[#9aa3b2]">{project.concept}</p>
            </Link>
            <button type="button" className="shrink-0 text-xs text-red-400" onClick={async (event) => {
              event.preventDefault();
              if (!window.confirm(`Supprimer \u00ab ${project.title} \u00bb ?`)) return;
              try {
                await api(`/api/projects/${project.id}/`, { method: "DELETE" });
                await load();
              } catch (err) {
                setError(String(err));
              }
            }}>Supprimer</button>
          </li>
        ))}
      </ul>
    </main>
  );
}

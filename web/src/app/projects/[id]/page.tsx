"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { api, mediaUrl } from "@/lib/api";

type BeatTake = { id: number; number: number; prompt: string; uri: string; status: string; backend: string };
type GenerationIngredient = { role?: string; key?: string; reference_uid?: string; uri?: string; name?: string };
type ShotTake = { id: number; number: number; prompt: string; uri: string; status: string; backend: string; generation_meta?: { ingredients?: GenerationIngredient[]; media_items?: GenerationIngredient[]; veo_reference_items?: GenerationIngredient[]; reference_uids?: string[]; previous_take?: { id?: number; number?: number; uri?: string } | null; language_locked?: boolean; dialogue_language_policy?: string; adjustment_prompt?: string } };
type Shot = { id: number; index: number; text: string; duration_seconds: number | string; video_prompt: string; reference_uids?: string[]; status: string; clip_uri?: string | null; takes: ShotTake[] };
type Scene = { id: number; index: number; heading: string; summary: string; time_of_day: string; lighting: string };
type Beat = {
  id: number;
  scene_id?: number | null;
  narrative_event_id?: number | null;
  index: number;
  text: string;
  word_count: number;
  status: string;
  clip_uri?: string | null;
  ingredients?: { role?: string; name?: string; uri?: string }[];
  takes: BeatTake[];
  shots: Shot[];
};
type PlannedScene = { index: number; heading: string; summary: string; location_id: string; time_of_day: string; character_ids: string[]; prop_ids: string[]; event_ids: string[]; target_seconds: number };
type ScenePlan = { id: number; version: number; payload: PlannedScene[]; locked: boolean; created_at: string };
type Episode = {
  id: number;
  number: number;
  title: string;
  logline: string;
  status: string;
  latest_script?: string;
  beats: Beat[];
  scenes: Scene[];
  scene_plans: ScenePlan[];
};
type Character = { id: number; key: string; name: string; role: string; look: string };
type Location = { id: number; key: string; name: string; look: string };
type Prop = { id: number; key: string; name: string; look: string; story_function?: string };
type Ref = { id: number; role: string; uri: string; provider?: string; meta?: { name?: string; key?: string; entity?: string; custom_prompt?: string } };
type Job = { id: number; kind: string; status: "queued" | "running" | "succeeded" | "failed" | "cancelled"; error?: string; result?: Record<string, unknown> };
type NarrativeEvent = { key: string; position: number; description: string; episode_number: number; status: string };
type NarrativeContract = { point_of_view: string; narrator: string; tense: string; story_type: string; recommended_episode_count: number; locked: boolean; events: NarrativeEvent[] };
type Project = {
  id: number;
  title: string;
  concept: string;
  delivery: string;
  visual_style: string;
  refs?: Ref[];
  narrative_contract?: NarrativeContract | null;
  bibles: { id: number; version: number; locked: boolean; characters: Character[]; locations: Location[]; props: Prop[] }[];
  seasons: { id: number; episodes: Episode[] }[];
};

export default function ProjectPage() {
  const params = useParams<{ id: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState<string>("");
  const [reframe, setReframe] = useState<Record<number, string>>({});
  const [previewRef, setPreviewRef] = useState<Ref | null>(null);
  const [showAddRef, setShowAddRef] = useState(false);
  const [newRef, setNewRef] = useState({ entity_type: "prop", name: "", look: "", role: "", time_of_day: "", story_function: "" });
  const [refJob, setRefJob] = useState<Job | null>(null);
  const [refNotice, setRefNotice] = useState("");
  const [promptRef, setPromptRef] = useState<Ref | null>(null);
  const [refPrompt, setRefPrompt] = useState("");
  const [shotJobs, setShotJobs] = useState<Record<number, Job>>({});
  const [shotAdjustments, setShotAdjustments] = useState<Record<number, string>>({});

  async function load() {
    setProject(await api<Project>(`/api/projects/${params.id}/`));
  }

  useEffect(() => {
    load().catch((err) => setError(String(err)));
  }, [params.id]);

  async function generateRefsWithProgress() {
    setBusy("refs");
    setError("");
    setRefNotice("Préparation de la génération…");
    try {
      const response = await api<{ job_id: number; status: Job["status"] }>(`/api/projects/${project?.id}/generate-refs/`, {
        method: "POST",
        body: JSON.stringify({}),
      });
      let job = await api<Job>(`/api/jobs/${response.job_id}/`);
      setRefJob(job);
      while (job.status === "queued" || job.status === "running") {
        setRefNotice(job.status === "queued" ? (job.error || "Génération en file d’attente…") : "Génération des références en cours…");
        await new Promise((resolve) => window.setTimeout(resolve, 2000));
        job = await api<Job>(`/api/jobs/${response.job_id}/`);
        setRefJob(job);
        await load();
      }
      await load();
      if (job.status === "succeeded") {
        setRefNotice("Références générées avec succès.");
      } else {
        setRefNotice("");
        setError(job.error || "La génération des références a échoué.");
      }
    } catch (err) {
      setRefNotice("");
      setError(String(err));
    } finally {
      setBusy("");
    }
  }

  async function generateShotTake(shotId: number) {
    const key = `render-shot-${shotId}`;
    setBusy(key);
    setError("");
    try {
      const response = await api<{ job_id: number; status: Job["status"] }>(`/api/shots/${shotId}/render/`, {
        method: "POST",
        body: JSON.stringify({ prompt: shotAdjustments[shotId] ?? "" }),
      });
      let job = await api<Job>(`/api/jobs/${response.job_id}/`);
      setShotJobs((current) => ({ ...current, [shotId]: job }));
      await load();
      while (job.status === "queued" || job.status === "running") {
        await new Promise((resolve) => window.setTimeout(resolve, 2000));
        job = await api<Job>(`/api/jobs/${response.job_id}/`);
        setShotJobs((current) => ({ ...current, [shotId]: job }));
        await load();
      }
      await load();
      if (job.status !== "succeeded") {
        setError(job.error || "La génération du take a échoué.");
      }
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy("");
    }
  }

  async function run(key: string, path: string, body: object = {}) {
    setBusy(key);
    setError("");
    try {
      await api(path, { method: "POST", body: JSON.stringify(body) });
      await load();
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy("");
    }
  }

  if (!project) {
    return <main className="px-6 py-12 text-[#9aa3b2]">{error || "Chargement…"}</main>;
  }

  const bible = project.bibles[0];
  const episodes = project.seasons[0]?.episodes ?? [];

  return (
    <main className="mx-auto flex max-w-4xl flex-col gap-8 px-6 py-12">
      <p className="text-sm tracking-[0.2em] text-[#e8c36a] uppercase">
        <Link href="/projects">Projets</Link>
      </p>
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-3xl font-semibold">{project.title}</h1>
          <p className="mt-2 text-[#9aa3b2]">{project.concept}</p>
          <p className="mt-1 text-xs uppercase tracking-[0.15em] text-[#e8c36a]">Mode · {project.delivery} · Style · {project.visual_style.replaceAll("_", " ")}</p>
        </div>
        <button
          className="text-xs text-red-400"
          onClick={async () => {
            if (!window.confirm(`Supprimer \u00ab ${project.title} \u00bb ?`)) return;
            try {
              await api(`/api/projects/${project.id}/`, { method: "DELETE" });
              window.location.href = "/projects";
            } catch (err) {
              setError(String(err));
            }
          }}
        >
          Supprimer le projet
        </button>
      </header>
      {error ? <p className="text-sm text-red-400">{error}</p> : null}
      <section className="space-y-3">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-xl">Bible {bible ? `v${bible.version}` : ""} {bible?.locked ? "\u00b7 verrouillée" : "\u00b7 brouillon"}</h2>
          <div className="flex gap-2">
            {bible && !bible.locked ? (
              <button onClick={() => run("lock", `/api/projects/${project.id}/lock-bible/`)} className="rounded-lg border border-[#e8c36a] px-3 py-1 text-xs text-[#e8c36a]">{busy === "lock" ? "\u2026" : "Verrouiller la bible"}</button>
            ) : null}
            {bible?.locked ? (
              <div className="flex gap-2">
                <button type="button" onClick={() => setShowAddRef((v) => !v)} className="rounded-lg border border-[#2a2e38] px-3 py-1 text-xs">{showAddRef ? "Annuler" : "+ Ajouter une ref"}</button>
                <button disabled={busy === "refs"} onClick={generateRefsWithProgress} className="rounded-lg border border-[#e8c36a] px-3 py-1 text-xs text-[#e8c36a] disabled:opacity-50">{busy === "refs" ? "Génération…" : "Générer les refs"}</button>
              </div>
            ) : null}
          </div>
        </div>
        {showAddRef && bible?.locked ? (
          <form className="space-y-3 rounded-xl border border-[#e8c36a]/40 bg-[#14161c] p-4" onSubmit={async (e) => {
            e.preventDefault(); setBusy("add-ref"); setError("");
            try {
              await api(`/api/projects/${project.id}/add-reference/`, { method: "POST", body: JSON.stringify(newRef) });
              setNewRef({ entity_type: "prop", name: "", look: "", role: "", time_of_day: "", story_function: "" });
              setShowAddRef(false); await load();
            } catch (err) { setError(String(err)); } finally { setBusy(""); }
          }}>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="text-xs text-[#9aa3b2]">Type<select value={newRef.entity_type} onChange={(e) => setNewRef((v) => ({...v, entity_type:e.target.value}))} className="mt-1 w-full rounded-lg border border-[#2a2e38] bg-[#0b0c10] px-3 py-2 text-sm text-white"><option value="character">Personnage</option><option value="location">Lieu</option><option value="prop">Objet / accessoire</option></select></label>
              <label className="text-xs text-[#9aa3b2]">Nom<input required value={newRef.name} onChange={(e) => setNewRef((v) => ({...v,name:e.target.value}))} placeholder="Ex. Bouilloire, tasse de thé" className="mt-1 w-full rounded-lg border border-[#2a2e38] bg-[#0b0c10] px-3 py-2 text-sm text-white" /></label>
            </div>
            <label className="block text-xs text-[#9aa3b2]">Description visuelle canonique<textarea required rows={3} value={newRef.look} onChange={(e) => setNewRef((v) => ({...v,look:e.target.value}))} placeholder="Apparence exacte à conserver dans tous les plans." className="mt-1 w-full rounded-lg border border-[#2a2e38] bg-[#0b0c10] px-3 py-2 text-sm text-white" /></label>
            {newRef.entity_type === "character" ? <label className="block text-xs text-[#9aa3b2]">Rôle<input value={newRef.role} onChange={(e) => setNewRef((v) => ({...v,role:e.target.value}))} className="mt-1 w-full rounded-lg border border-[#2a2e38] bg-[#0b0c10] px-3 py-2 text-sm text-white" /></label> : null}
            {newRef.entity_type === "location" ? <label className="block text-xs text-[#9aa3b2]">Moment / ambiance<input value={newRef.time_of_day} onChange={(e) => setNewRef((v) => ({...v,time_of_day:e.target.value}))} placeholder="Ex. 02h00, nuit" className="mt-1 w-full rounded-lg border border-[#2a2e38] bg-[#0b0c10] px-3 py-2 text-sm text-white" /></label> : null}
            {newRef.entity_type === "prop" ? <label className="block text-xs text-[#9aa3b2]">Fonction dans l'histoire<input value={newRef.story_function} onChange={(e) => setNewRef((v) => ({...v,story_function:e.target.value}))} placeholder="Ex. Présente dans plusieurs épisodes." className="mt-1 w-full rounded-lg border border-[#2a2e38] bg-[#0b0c10] px-3 py-2 text-sm text-white" /></label> : null}
            <button disabled={busy === "add-ref"} className="rounded-lg bg-[#e8c36a] px-4 py-2 text-sm font-medium text-[#0b0c10] disabled:opacity-50">{busy === "add-ref" ? "Ajout…" : "Ajouter à la Bible"}</button>
            <p className="text-xs text-[#9aa3b2]">L'élément devient canonique. « Générer les refs » créera ensuite uniquement son image manquante dans le style du projet.</p>
          </form>
        ) : null}
        <div className="grid gap-3 sm:grid-cols-2">
          {(bible?.characters ?? []).map((c) => (
            <article key={c.id} className="rounded-xl border border-[#2a2e38] bg-[#14161c] p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-medium">{c.name}</p>
                  <p className="text-xs text-[#e8c36a]">{c.role}</p>
                </div>
                {bible?.locked ? (
                  <button
                    onClick={() => run(
                      `char-ref-${c.id}`,
                      `/api/projects/${project.id}/regenerate-reference/`,
                      { entity_type: "character", entity_key: c.key },
                    )}
                    className="rounded-lg border border-[#e8c36a] px-2 py-1 text-[11px] text-[#e8c36a]"
                  >
                    {busy === `char-ref-${c.id}` ? "Génération…" : "Régénérer la ref"}
                  </button>
                ) : null}
              </div>
              <p className="mt-2 text-sm text-[#9aa3b2]">{c.look}</p>
            </article>
          ))}
          {(bible?.locations ?? []).map((l) => (
            <article key={l.id} className="rounded-xl border border-[#2a2e38] bg-[#14161c] p-4">
              <div className="flex items-start justify-between gap-3">
                <p className="font-medium">{l.name}</p>
                {bible?.locked ? (
                  <button onClick={() => run(`loc-ref-${l.id}`, `/api/projects/${project.id}/regenerate-reference/`, { entity_type: "location", entity_key: l.key })} className="rounded-lg border border-[#e8c36a] px-2 py-1 text-[11px] text-[#e8c36a]">
                    {busy === `loc-ref-${l.id}` ? "Génération…" : "Régénérer la ref"}
                  </button>
                ) : null}
              </div>
              <p className="mt-2 text-sm text-[#9aa3b2]">{l.look}</p>
            </article>
          ))}
          {(bible?.props ?? []).map((p) => (
            <article key={`prop-${p.id}`} className="rounded-xl border border-[#2a2e38] bg-[#14161c] p-4">
              <div className="flex items-start justify-between gap-3">
                <div><p className="font-medium">{p.name}</p><p className="text-xs text-[#e8c36a]">Objet / accessoire</p></div>
                {bible?.locked ? (
                  <button onClick={() => run(`prop-ref-${p.id}`, `/api/projects/${project.id}/regenerate-reference/`, { entity_type: "prop", entity_key: p.key })} className="rounded-lg border border-[#e8c36a] px-2 py-1 text-[11px] text-[#e8c36a]">
                    {busy === `prop-ref-${p.id}` ? "Génération…" : "Régénérer la ref"}
                  </button>
                ) : null}
              </div>
              <p className="mt-2 text-sm text-[#9aa3b2]">{p.look}</p>
            </article>
          ))}
        </div>
      </section>
      <section className="space-y-4">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-xl">Assets visuels</h2>
          <span className="text-xs text-[#9aa3b2]">{project.refs?.length ?? 0} référence(s)</span>
        </div>
        {(busy === "refs" || refNotice) ? (
          <div className="rounded-xl border border-[#e8c36a]/40 bg-[#14161c] p-4">
            <div className="flex items-center gap-3">
              {busy === "refs" ? <span className="h-4 w-4 animate-spin rounded-full border-2 border-[#e8c36a] border-t-transparent" /> : <span className="text-green-400">✓</span>}
              <div>
                <p className="text-sm font-medium">{refNotice || "Génération en cours…"}</p>
                {refJob ? <p className="mt-1 text-xs text-[#9aa3b2]">Job #{refJob.id} · {refJob.status} · les nouvelles images apparaissent automatiquement ci-dessous.</p> : null}
              </div>
            </div>
          </div>
        ) : null}
        {project.refs?.length ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {project.refs.map((ref) => (
              <article key={ref.id} className="overflow-hidden rounded-xl border border-[#2a2e38] bg-[#14161c]">
                <button
                  type="button"
                  onClick={() => setPreviewRef(ref)}
                  className="block w-full cursor-zoom-in focus:outline-none focus:ring-2 focus:ring-[#e8c36a]"
                  aria-label={`Voir la référence ${ref.meta?.name ?? ref.meta?.key ?? ref.role}`}
                >
                  <img
                    src={mediaUrl(ref.uri)}
                    alt={ref.meta?.name ?? ref.meta?.key ?? ref.role}
                    className="aspect-video w-full bg-[#0b0c10] object-cover"
                  />
                </button>
                <div className="p-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="truncate font-medium">{ref.meta?.name ?? ref.meta?.key ?? "Référence"}</p>
                      <p className="mt-1 text-xs uppercase tracking-[0.12em] text-[#e8c36a]">{ref.role.replaceAll("_", " ")}</p>
                      <p className="mt-1 truncate text-xs text-[#9aa3b2]">{ref.provider || "provider inconnu"}</p>
                    </div>
                    <div className="flex shrink-0 flex-col items-end gap-2">
                      <button
                        type="button"
                        onClick={() => { setPromptRef(ref); setRefPrompt(ref.meta?.custom_prompt ?? ""); }}
                        className="text-xs text-[#e8c36a]"
                      >
                        Affiner / Régénérer
                      </button>
                      <button
                        type="button"
                        disabled={busy === `delete-ref-${ref.id}`}
                        onClick={async () => {
                          const name = ref.meta?.name ?? ref.meta?.key ?? "cette référence";
                          if (!window.confirm(`Supprimer l'image de référence « ${name} » ? L'élément restera dans la Bible et pourra être régénéré.`)) return;
                          await run(`delete-ref-${ref.id}`, `/api/projects/${project.id}/delete-reference/`, { asset_id: ref.id });
                        }}
                        className="text-xs text-red-400 disabled:opacity-50"
                      >
                        {busy === `delete-ref-${ref.id}` ? "…" : "Supprimer"}
                      </button>
                    </div>
                  </div>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <p className="rounded-xl border border-dashed border-[#2a2e38] p-4 text-sm text-[#9aa3b2]">
            Aucune référence visuelle enregistrée pour ce projet.
          </p>
        )}
      </section>
      {project.narrative_contract ? (
        <section className="space-y-3">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-xl">Contrat narratif</h2>
            <span className="rounded-full border border-[#2a2e38] px-2 py-1 text-xs text-[#9aa3b2]">{project.narrative_contract.locked ? "verrouillé" : "brouillon"}</span>
          </div>
          <div className="rounded-xl border border-[#2a2e38] bg-[#14161c] p-4">
            <p className="text-sm text-[#9aa3b2]">POV · {project.narrative_contract.point_of_view} · Narrateur · {project.narrative_contract.narrator} · Temps · {project.narrative_contract.tense} · {project.narrative_contract.recommended_episode_count} épisode(s)</p>
            <ol className="mt-3 space-y-2">
              {project.narrative_contract.events.map((event) => (
                <li key={event.key} className="flex gap-3 rounded-lg bg-[#0b0c10] px-3 py-2 text-sm">
                  <span className="shrink-0 font-medium text-[#e8c36a]">{event.key}</span>
                  <span className="min-w-0 flex-1">{event.description}</span>
                  <span className="shrink-0 text-xs text-[#9aa3b2]">E{event.episode_number} · {event.status}</span>
                </li>
              ))}
            </ol>
          </div>
        </section>
      ) : null}
      <section className="space-y-4">
        <h2 className="text-xl">Épisodes</h2>
        {episodes.map((ep) => (
          <article key={ep.id} className="rounded-xl border border-[#2a2e38] bg-[#14161c] p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-medium">E{ep.number} \u00b7 {ep.title}</p>
                <p className="text-sm text-[#9aa3b2]">{ep.logline}</p>
              </div>
              <div className="flex flex-col gap-2">
                <button onClick={() => run(`scr-${ep.id}`, `/api/episodes/${ep.id}/write-script/`)} className="rounded-lg border border-[#e8c36a] px-3 py-1 text-xs text-[#e8c36a]">{busy === `scr-${ep.id}` ? "\u2026" : "Écrire le script"}</button>
                <button onClick={() => run(`plan-${ep.id}`, `/api/episodes/${ep.id}/plan-scenes/`)} className="rounded-lg border border-[#2a2e38] px-3 py-1 text-xs">{busy === `plan-${ep.id}` ? "…" : ep.scene_plans?.length ? "Régénérer le Scene Plan" : "Générer le Scene Plan"}</button>
                <button disabled={!ep.scene_plans?.some((plan) => plan.locked)} onClick={() => run(`seg-${ep.id}`, `/api/episodes/${ep.id}/segment/`)} className="rounded-lg border border-[#2a2e38] px-3 py-1 text-xs disabled:opacity-40">{busy === `seg-${ep.id}` ? "…" : "Découper en beats"}</button>
              </div>
            </div>
            {ep.scene_plans?.length ? (() => {
              const plan = ep.scene_plans[0];
              return <div className="mt-4 rounded-xl border border-[#2a2e38] bg-[#0b0c10] p-3">
                <div className="flex items-center justify-between gap-3">
                  <div><p className="text-sm font-medium">Scene Plan v{plan.version}</p><p className="text-xs text-[#9aa3b2]">{plan.locked ? "Verrouillé · utilisé pour les beats" : "À vérifier avant segmentation"}</p></div>
                  {!plan.locked ? <button onClick={() => run(`lock-plan-${ep.id}`, `/api/episodes/${ep.id}/lock-scene-plan/`, { scene_plan_id: plan.id })} className="rounded-lg border border-[#e8c36a] px-3 py-1 text-xs text-[#e8c36a]">{busy === `lock-plan-${ep.id}` ? "…" : "Verrouiller"}</button> : <span className="text-xs text-green-400">✓ verrouillé</span>}
                </div>
                <div className="mt-3 space-y-2">{plan.payload.map((scene) => <div key={scene.index} className="rounded-lg border border-[#2a2e38] px-3 py-2 text-xs"><p className="font-medium">Scène {scene.index} · {scene.heading || scene.location_id} · {scene.target_seconds}s</p><p className="mt-1 text-[#9aa3b2]">{scene.summary}</p><p className="mt-1 text-[#e8c36a]">{scene.location_id} · {scene.time_of_day} · {(scene.event_ids || []).join(" ")}</p></div>)}</div>
              </div>;
            })() : ep.latest_script ? <p className="mt-3 text-xs text-[#9aa3b2]">Génère et verrouille le Scene Plan avant le découpage en beats.</p> : null}
            {ep.scenes?.length ? <div className="mt-3 flex flex-wrap gap-2">{ep.scenes.map((scene) => <span key={scene.id} className="rounded-full border border-[#2a2e38] px-2 py-1 text-xs text-[#9aa3b2]">Scène {scene.index} · {scene.heading || "Sans titre"}</span>)}</div> : null}
            {ep.beats.length ? (
              <ol className="mt-3 space-y-2">
                {ep.beats.map((beat) => (
                  <li key={beat.id} className="space-y-2 rounded-lg bg-[#0b0c10] px-3 py-2 text-sm">
                    <p>
                      <span className="mr-2 text-[#e8c36a]">{String(beat.index + 1).padStart(2, "0")} \u00b7 {beat.word_count} mots \u00b7 {beat.status}</span>
                      {beat.text}
                    </p>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded-full border border-[#2a2e38] px-2 py-0.5 text-[10px] uppercase tracking-[0.12em] text-[#9aa3b2]">Beat narratif</span>
                      <button onClick={() => run(`shots-${beat.id}`, `/api/beats/${beat.id}/plan-shots/`)} className="rounded border border-[#e8c36a] px-2 py-0.5 text-xs text-[#e8c36a]">{busy === `shots-${beat.id}` ? "…" : beat.shots?.length ? "Shots préparés" : "Préparer les shots"}</button>
                    </div>
                    {beat.shots?.length ? (
                      <div className="space-y-2 border-l border-[#2a2e38] pl-3">
                        {beat.shots.map((shot) => (
                          <div key={shot.id} className="rounded-lg border border-[#2a2e38] bg-[#14161c] p-3">
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <p className="text-xs font-medium text-[#e8c36a]">Shot vidéo {shot.index} · {Number(shot.duration_seconds).toFixed(1)}s · {shot.status}</p>
                              <button disabled={busy === `render-shot-${shot.id}` || shotJobs[shot.id]?.status === "queued" || shotJobs[shot.id]?.status === "running"} onClick={() => generateShotTake(shot.id)} className="rounded border border-[#e8c36a] px-2 py-1 text-xs text-[#e8c36a] disabled:cursor-wait disabled:opacity-50">{shotJobs[shot.id]?.status === "queued" ? "En file d’attente…" : shotJobs[shot.id]?.status === "running" ? "Vidéo en génération…" : busy === `render-shot-${shot.id}` ? "Démarrage…" : "Générer un take"}</button>
                            </div>
                            {shotJobs[shot.id]?.status === "queued" || shotJobs[shot.id]?.status === "running" ? <div className="mt-2 rounded border border-[#e8c36a]/30 bg-[#e8c36a]/5 px-3 py-2 text-xs text-[#e8c36a]"><p>{shotJobs[shot.id]?.status === "queued" ? "Take en file d’attente. Tu peux continuer à travailler, cette zone se met à jour automatiquement." : "Veo génère le clip. La vidéo apparaîtra ici automatiquement dès qu’elle sera prête."}</p><div className="mt-2 h-1 overflow-hidden rounded bg-[#2a2e38]"><div className="h-full w-1/2 animate-pulse rounded bg-[#e8c36a]" /></div></div> : null}
                            {shotJobs[shot.id]?.status === "succeeded" ? <p className="mt-2 text-xs text-green-400">✓ Take généré. La vidéo est prête à être visionnée et verrouillée.</p> : null}
                            <p className="mt-2 text-xs text-[#9aa3b2]">{shot.video_prompt || shot.text}</p>
                            {shot.reference_uids?.length ? (
                              <div className="mt-2 rounded-lg border border-[#2a2e38] bg-[#0b0c10] p-2">
                                <p className="text-[10px] uppercase tracking-[0.12em] text-[#e8c36a]">Références verrouillées pour ce shot · {shot.reference_uids.length}</p>
                                <div className="mt-1 flex flex-wrap gap-1">
                                  {shot.reference_uids.map((uid) => {
                                    const ref = project.refs?.find((candidate) => candidate.reference_uid === uid || candidate.meta?.reference_uid === uid);
                                    return <div key={uid} className="flex items-center gap-1 rounded border border-[#2a2e38] px-1.5 py-1 text-[10px]">
                                      {ref?.uri ? <img src={mediaUrl(ref.uri)} alt={ref.meta?.name ?? ref.meta?.key ?? uid} className="h-8 w-8 rounded object-cover" /> : null}
                                      <span>{ref?.meta?.name ?? ref?.meta?.key ?? "Référence"}</span>
                                      <code className="text-[#6f7785]">{uid}</code>
                                    </div>;
                                  })}
                                </div>
                              </div>
                            ) : <p className="mt-2 text-[10px] text-red-300">Aucune référence verrouillée sur ce shot.</p>}
                            <div className="mt-2 flex flex-wrap gap-2">
                              <input
                                maxLength={4000}
                                value={shotAdjustments[shot.id] ?? ""}
                                onChange={(e) => setShotAdjustments((current) => ({ ...current, [shot.id]: e.target.value }))}
                                placeholder="Réajuster le prochain take… ex. caméra plus proche, jeu plus retenu, lumière plus chaude"
                                className="min-w-56 flex-1 rounded border border-[#2a2e38] bg-[#0b0c10] px-2 py-1 text-xs outline-none focus:border-[#e8c36a]"
                              />
                              <span className="self-center text-[10px] text-[#6f7785]">Identité, refs, langue et dialogue restent verrouillés.</span>
                            </div>
                            {shot.clip_uri ? <video controls className="mt-2 max-h-64 w-full rounded bg-black" src={mediaUrl(shot.clip_uri)} /> : null}
                            {shot.takes?.length ? <div className="mt-2 flex flex-wrap gap-2">{shot.takes.map((take) => (
                              <div key={take.id} className="flex items-center gap-2 rounded border border-[#2a2e38] px-2 py-1 text-xs">
                                <span>Take {take.number} · {take.status}</span>
                                {take.uri && take.status !== "locked" ? <button onClick={() => run(`lock-shot-take-${take.id}`, `/api/shots/${shot.id}/review/`, { decision: "approve", take_id: take.id })} className="text-[#e8c36a]">Verrouiller</button> : null}
                                {take.status === "locked" ? <span className="text-green-400">✓ choisi</span> : null}
                                {take.uri && take.status !== "locked" ? <button onClick={() => run(`reject-shot-take-${take.id}`, `/api/shots/${shot.id}/review/`, { decision: "reject", take_id: take.id })} className="text-red-300">Rejeter</button> : null}
                                {take.generation_meta?.ingredients?.length ? (
                                  <details className="w-full basis-full border-t border-[#2a2e38] pt-2">
                                    <summary className="cursor-pointer text-[10px] uppercase tracking-[0.12em] text-[#e8c36a]">Références Veo · {take.generation_meta.veo_reference_items?.length ?? 0} envoyée(s)</summary>
                                    <div className="mt-2 space-y-1">
                                      {(take.generation_meta.media_items ?? take.generation_meta.ingredients).map((item, refIndex) => (
                                        <div key={item.reference_uid ?? `${item.key}-${refIndex}`} className="flex flex-wrap items-center gap-2 rounded bg-[#0b0c10] px-2 py-1 text-[10px]">
                                          <span className="text-[#e8c36a]">#{refIndex + 1}</span>
                                          <span>{item.role?.replaceAll("_", " ")}</span>
                                          <span className="font-medium">{item.name ?? item.key ?? "ref"}</span>
                                          {item.reference_uid ? <code className="text-[#9aa3b2]">UID {item.reference_uid}</code> : null}
                                          {take.generation_meta?.veo_reference_items?.some((sent) => sent.reference_uid === item.reference_uid) ? <span className="text-green-400">✓ envoyée à Veo</span> : <span className="text-[#6f7785]">verrou logique</span>}
                                        </div>
                                      ))}
                                      {take.generation_meta.previous_take?.number ? <p className="text-[10px] text-[#9aa3b2]">Baseline · Take {take.generation_meta.previous_take.number}</p> : null}
                                      {take.generation_meta.language_locked ? <p className="text-[10px] text-green-400">✓ Langue/dialogue verrouillés · {take.generation_meta.dialogue_language_policy ?? "langue originale"}</p> : null}
                                      {take.generation_meta.adjustment_prompt ? <p className="text-[10px] text-[#9aa3b2]">Réajustement · {take.generation_meta.adjustment_prompt}</p> : null}
                                    </div>
                                  </details>
                                ) : null}
                              </div>
                            ))}</div> : <p className="mt-2 text-[11px] text-[#6f7785]">Aucun take généré pour ce shot.</p>}
                          </div>
                        ))}
                      </div>
                    ) : <p className="text-[11px] text-[#6f7785]">Ce beat raconte l’histoire. Prépare ses shots avant toute génération vidéo.</p>}
                    <div className="flex flex-wrap gap-2">
                      <input
                        className="min-w-48 flex-1 rounded border border-[#2a2e38] bg-[#14161c] px-2 py-1 text-xs outline-none"
                        placeholder="Recadrer ce beat… ex. Marc décroche à 03h14, la voix parle du pont"
                        value={reframe[beat.id] ?? ""}
                        onChange={(e) => setReframe((cur) => ({ ...cur, [beat.id]: e.target.value }))}
                      />
                      <button
                        onClick={() => run(`rw-${beat.id}`, `/api/beats/${beat.id}/recontextualize/`, { prompt: reframe[beat.id] ?? "" })}
                        className="rounded border border-[#e8c36a] px-2 py-0.5 text-xs text-[#e8c36a]"
                      >
                        {busy === `rw-${beat.id}` ? "\u2026" : "Recadrer"}
                      </button>
                    </div>
                  </li>
                ))}
              </ol>
            ) : null}
          </article>
        ))}
      </section>
      {promptRef ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 p-4" role="dialog" aria-modal="true" onClick={() => setPromptRef(null)}>
          <form
            className="w-full max-w-2xl space-y-4 rounded-xl border border-[#2a2e38] bg-[#14161c] p-5"
            onClick={(e) => e.stopPropagation()}
            onSubmit={async (e) => {
              e.preventDefault();
              const entityType = promptRef.meta?.entity || (promptRef.role.includes("character") ? "character" : promptRef.role.includes("location") ? "location" : "prop");
              const entityKey = promptRef.meta?.key;
              if (!entityKey) { setError("Cette référence ne possède pas de clé canonique."); return; }
              const key = `prompt-ref-${promptRef.id}`;
              setBusy(key); setError("");
              try {
                await api(`/api/projects/${project.id}/regenerate-reference/`, {
                  method: "POST",
                  body: JSON.stringify({ entity_type: entityType, entity_key: entityKey, custom_prompt: refPrompt }),
                });
                setPromptRef(null);
                await load();
              } catch (err) { setError(String(err)); } finally { setBusy(""); }
            }}
          >
            <div>
              <p className="text-lg font-medium">Affiner la référence · {promptRef.meta?.name ?? promptRef.meta?.key ?? "Référence"}</p>
              <p className="mt-1 text-xs text-[#9aa3b2]">La Bible et le style du projet restent prioritaires. Ajoute seulement les détails visuels que tu veux préciser pour cette génération.</p>
            </div>
            <textarea
              autoFocus
              maxLength={4000}
              rows={7}
              value={refPrompt}
              onChange={(e) => setRefPrompt(e.target.value)}
              placeholder="Ex. conserver exactement le même visage, ajouter une veste noire légèrement usée, expression plus fatiguée, lumière latérale douce…"
              className="w-full rounded-lg border border-[#2a2e38] bg-[#0b0c10] px-3 py-3 text-sm text-white outline-none focus:border-[#e8c36a]"
            />
            <div className="flex items-center justify-between gap-3">
              <span className="text-xs text-[#9aa3b2]">{refPrompt.length}/4000</span>
              <div className="flex gap-2">
                <button type="button" onClick={() => setPromptRef(null)} className="rounded-lg border border-[#2a2e38] px-4 py-2 text-sm">Annuler</button>
                <button disabled={busy === `prompt-ref-${promptRef.id}`} className="rounded-lg bg-[#e8c36a] px-4 py-2 text-sm font-medium text-[#0b0c10] disabled:opacity-50">
                  {busy === `prompt-ref-${promptRef.id}` ? "Régénération en cours…" : "Régénérer avec ce prompt"}
                </button>
              </div>
            </div>
          </form>
        </div>
      ) : null}
      {previewRef ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 p-4"
          role="dialog"
          aria-modal="true"
          aria-label="Aperçu de la référence visuelle"
          onClick={() => setPreviewRef(null)}
        >
          <div
            className="flex max-h-[92vh] max-w-6xl flex-col overflow-hidden rounded-xl border border-[#2a2e38] bg-[#0b0c10]"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="flex items-center justify-between gap-4 border-b border-[#2a2e38] px-4 py-3">
              <div className="min-w-0">
                <p className="truncate font-medium">
                  {previewRef.meta?.name ?? previewRef.meta?.key ?? "Référence"}
                </p>
                <p className="text-xs uppercase tracking-[0.12em] text-[#e8c36a]">
                  {previewRef.role.replaceAll("_", " ")}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setPreviewRef(null)}
                className="rounded-lg border border-[#2a2e38] px-3 py-2 text-sm"
              >
                Fermer
              </button>
            </div>
            <div className="overflow-auto p-3">
              <img
                src={mediaUrl(previewRef.uri)}
                alt={previewRef.meta?.name ?? previewRef.meta?.key ?? previewRef.role}
                className="mx-auto max-h-[78vh] max-w-full object-contain"
              />
            </div>
          </div>
        </div>
      ) : null}
    </main>
  );
}

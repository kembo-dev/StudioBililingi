"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { api, mediaUrl } from "@/lib/api";

type BeatTake = { id: number; number: number; prompt: string; uri: string; status: string; backend: string };
type GenerationIngredient = { role?: string; key?: string; reference_uid?: string; uri?: string; name?: string };
type ShotTake = { id: number; number: number; prompt: string; uri: string; status: string; backend: string; generation_meta?: { ingredients?: GenerationIngredient[]; media_items?: GenerationIngredient[]; veo_reference_items?: GenerationIngredient[]; reference_uids?: string[]; previous_take?: { id?: number; number?: number; uri?: string } | null; previous_take_frame?: string | null; language_locked?: boolean; dialogue_language_policy?: string; adjustment_prompt?: string; adjustment_mode?: string; adjustment_reference_uri?: string | null } };
type Shot = { id: number; index: number; text: string; duration_seconds: number | string; video_prompt: string; reference_uids?: string[]; status: string; clip_uri?: string | null; takes: ShotTake[] };
type Scene = { id: number; index: number; heading: string; summary: string; time_of_day: string; lighting: string };
type Beat = {
  id: number;
  scene_id?: number | null;
  narrative_event_id?: number | null;
  speaker_id?: number | null;
  index: number;
  text: string;
  word_count: number;
  status: string;
  speech_mode?: "silent" | "narration" | "dialogue" | "mixed";
  narration?: string;
  dialogue?: string;
  clip_uri?: string | null;
  ingredients?: { role?: string; name?: string; uri?: string }[];
  takes: BeatTake[];
  shots: Shot[];
  scene_frames?: { id: number; uri: string; provider?: string; meta?: { locked?: boolean; custom_prompt?: string } }[];
  usage?: { prompt_tokens_estimated: number; video_generations: number; video_seconds_requested: number; video_seconds_successful: number };
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
  episode_cut?: { id: number; uri: string; provider: string; meta?: Record<string, unknown> } | null;
  assembly_readiness?: { ready: boolean; total_shots: number; locked_shots: number; total_beats?: number; locked_beats?: number; beat_indexes_need_normalization?: boolean; beat_index_sequence?: number[]; missing: string[]; beat_progress?: { beat_id: number; beat_index: number; total_shots: number; locked_shots: number; status: "locked" | "needs_revision" | "in_progress" | "not_prepared" }[]; blockers?: { beat_id: number; beat_index: number; shot_id: number | null; shot_index: number | null; take_id: number | null; take_number: number | null; take_status: string; has_video: boolean; reason?: string; feedback?: string; label: string }[] };
};
type Character = { id: number; key: string; name: string; role: string; look: string };
type Location = { id: number; key: string; name: string; look: string };
type Prop = { id: number; key: string; name: string; look: string; story_function?: string };
type Ref = { id: number; role: string; uri: string; provider?: string; reference_uid?: string; meta?: { name?: string; key?: string; entity?: string; custom_prompt?: string; reference_uid?: string } };
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
  usage?: { prompt_tokens_estimated: number; video_generations: number; video_regenerations: number; failed_video_generations: number; video_seconds_requested: number; video_seconds_successful: number; note?: string; episodes?: { episode_id: number; episode_number: number; title: string; prompt_tokens_estimated: number; video_generations: number; video_regenerations: number; failed_video_generations: number; video_seconds_requested: number; video_seconds_successful: number }[] };
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
  const [reframeOpen, setReframeOpen] = useState<Record<number, boolean>>({});
  const [sceneFramePrompts, setSceneFramePrompts] = useState<Record<number, string>>({});
  const [sceneFrameRefs, setSceneFrameRefs] = useState<Record<number, { uri: string; name: string }>>({});
  const [previewRef, setPreviewRef] = useState<Ref | null>(null);
  const [showAddRef, setShowAddRef] = useState(false);
  const [newRef, setNewRef] = useState({ entity_type: "prop", name: "", look: "", role: "", time_of_day: "", story_function: "" });
  const [refJob, setRefJob] = useState<Job | null>(null);
  const [refNotice, setRefNotice] = useState("");
  const [promptRef, setPromptRef] = useState<Ref | null>(null);
  const [refPrompt, setRefPrompt] = useState("");
  const [shotJobs, setShotJobs] = useState<Record<number, Job>>({});
  const [shotAdjustments, setShotAdjustments] = useState<Record<number, string>>({});
  const [shotAdjustmentRefs, setShotAdjustmentRefs] = useState<Record<number, { uri: string; name: string }>>({});
  const [shotAdjustmentModes, setShotAdjustmentModes] = useState<Record<number, "custom" | "language" | "script">>({});

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

  async function uploadSceneFrameRef(beatId: number, file: File) {
    const key = `upload-scene-frame-ref-${beatId}`;
    setBusy(key);
    setError("");
    try {
      const form = new FormData();
      form.append("file", file);
      const uploaded = await api<{ uri: string; name: string }>(`/api/beats/${beatId}/upload-scene-frame-reference/`, {
        method: "POST",
        body: form,
      });
      setSceneFrameRefs((current) => ({ ...current, [beatId]: uploaded }));
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy("");
    }
  }

  async function regenerateSceneFrame(beatId: number) {
    await run(`scene-frame-${beatId}`, `/api/beats/${beatId}/generate-scene-frame/`, {
      prompt: sceneFramePrompts[beatId] ?? "",
      reference_uri: sceneFrameRefs[beatId]?.uri ?? "",
    });
  }

  async function uploadShotAdjustmentRef(shotId: number, file: File) {
    const key = `upload-shot-ref-${shotId}`;
    setBusy(key);
    setError("");
    try {
      const form = new FormData();
      form.append("file", file);
      const uploaded = await api<{ uri: string; name: string }>(`/api/shots/${shotId}/upload-adjustment-reference/`, {
        method: "POST",
        body: form,
      });
      setShotAdjustmentRefs((current) => ({ ...current, [shotId]: uploaded }));
    } catch (err) {
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
        body: JSON.stringify({
          prompt: shotAdjustments[shotId] ?? "",
          adjustment_reference_uri: shotAdjustmentRefs[shotId]?.uri ?? "",
          adjustment_mode: shotAdjustmentModes[shotId] ?? "custom",
        }),
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
      {project.usage ? (
        <section className="space-y-3">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-xl">Consommation de production</h2>
            <span className="text-xs text-[#9aa3b2]">Projet complet</span>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            <div className="rounded-xl border border-[#2a2e38] bg-[#14161c] p-3"><p className="text-[10px] uppercase text-[#9aa3b2]">Tokens prompt</p><p className="mt-1 text-lg font-medium">≈ {project.usage.prompt_tokens_estimated.toLocaleString()}</p></div>
            <div className="rounded-xl border border-[#2a2e38] bg-[#14161c] p-3"><p className="text-[10px] uppercase text-[#9aa3b2]">Générations vidéo</p><p className="mt-1 text-lg font-medium">{project.usage.video_generations}</p></div>
            <div className="rounded-xl border border-[#2a2e38] bg-[#14161c] p-3"><p className="text-[10px] uppercase text-[#9aa3b2]">Régénérations</p><p className="mt-1 text-lg font-medium">{project.usage.video_regenerations}</p></div>
            <div className="rounded-xl border border-[#2a2e38] bg-[#14161c] p-3"><p className="text-[10px] uppercase text-[#9aa3b2]">Vidéo demandée</p><p className="mt-1 text-lg font-medium">{project.usage.video_seconds_requested.toFixed(0)}s</p></div>
            <div className="rounded-xl border border-[#2a2e38] bg-[#14161c] p-3"><p className="text-[10px] uppercase text-[#9aa3b2]">Échecs</p><p className="mt-1 text-lg font-medium">{project.usage.failed_video_generations}</p></div>
          </div>
          {project.usage.episodes?.length ? (
            <div className="overflow-x-auto rounded-xl border border-[#2a2e38] bg-[#14161c]">
              <table className="w-full text-left text-xs">
                <thead className="text-[#9aa3b2]"><tr><th className="p-3">Épisode</th><th className="p-3">Tokens</th><th className="p-3">Générations</th><th className="p-3">Régénérations</th><th className="p-3">Secondes</th><th className="p-3">Échecs</th></tr></thead>
                <tbody>{project.usage.episodes.map((row) => <tr key={row.episode_id} className="border-t border-[#2a2e38]"><td className="p-3">E{row.episode_number} · {row.title}</td><td className="p-3">≈ {row.prompt_tokens_estimated.toLocaleString()}</td><td className="p-3">{row.video_generations}</td><td className="p-3">{row.video_regenerations}</td><td className="p-3">{row.video_seconds_requested.toFixed(0)}s</td><td className="p-3">{row.failed_video_generations}</td></tr>)}</tbody>
              </table>
            </div>
          ) : null}
          <p className="text-[10px] text-[#6f7785]">{project.usage.note}</p>
        </section>
      ) : null}
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
                <button
                  disabled={!ep.assembly_readiness?.ready || busy === `assemble-${ep.id}`}
                  onClick={() => run(`assemble-${ep.id}`, `/api/episodes/${ep.id}/assemble/`)}
                  className="rounded-lg border border-green-500/60 px-3 py-1 text-xs text-green-400 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {busy === `assemble-${ep.id}` ? "Assemblage…" : ep.episode_cut ? "Réassembler l’épisode" : "Assembler l’épisode"}
                </button>
              </div>
            </div>
            {ep.beats.length ? (
              <div className="mt-4 rounded-xl border border-[#2a2e38] bg-[#0b0c10] p-3">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-medium">Montage final de l’épisode</p>
                    <p className="text-xs text-[#9aa3b2]">
                      {ep.assembly_readiness?.locked_shots ?? 0}/{ep.assembly_readiness?.total_shots ?? 0} shots avec un take verrouillé
                    </p>
                  </div>
                  {ep.assembly_readiness?.ready ? <span className="text-xs text-green-400">✓ prêt à assembler</span> : <span className="text-xs text-amber-300">Verrouille tous les takes avant l’assemblage</span>}
                </div>
                {ep.assembly_readiness?.beat_indexes_need_normalization ? (
                  <div className="mt-3 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-amber-400/40 bg-amber-400/5 p-3">
                    <div>
                      <p className="text-xs font-medium text-amber-300">Ancienne numérotation de beats détectée</p>
                      <p className="text-[10px] text-[#9aa3b2]">Répare uniquement les index. Les beats, shots, takes, refs et médias conservent leurs identifiants.</p>
                    </div>
                    <button type="button" onClick={() => run(`normalize-beats-${ep.id}`, `/api/episodes/${ep.id}/normalize-beat-indexes/`)} className="rounded border border-amber-400/60 px-3 py-1 text-xs text-amber-300">
                      {busy === `normalize-beats-${ep.id}` ? "Réparation…" : "Réparer la numérotation"}
                    </button>
                  </div>
                ) : null}
                {ep.assembly_readiness?.beat_progress?.length ? (
                  <div className="mt-3 rounded-lg border border-[#2a2e38] bg-[#0b0c10] p-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <p className="text-xs font-medium text-white">Progression des beats</p>
                        <p className="text-[10px] text-[#9aa3b2]">{ep.assembly_readiness.locked_beats ?? 0}/{ep.assembly_readiness.total_beats ?? ep.assembly_readiness.beat_progress.length} beats prêts pour le montage</p>
                      </div>
                      <div className="h-1.5 w-40 overflow-hidden rounded bg-[#2a2e38]">
                        <div className="h-full rounded bg-green-500 transition-all" style={{ width: `${Math.round(((ep.assembly_readiness.locked_beats ?? 0) / Math.max(1, ep.assembly_readiness.total_beats ?? ep.assembly_readiness.beat_progress.length)) * 100)}%` }} />
                      </div>
                    </div>
                    <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                      {ep.assembly_readiness.beat_progress.map((item) => (
                        <button key={item.beat_id} type="button" onClick={() => document.getElementById(`beat-${item.beat_id}`)?.scrollIntoView({ behavior: "smooth", block: "center" })} className={`flex items-center justify-between rounded border px-3 py-2 text-left transition hover:bg-white/5 ${item.status === "locked" ? "border-green-500/40 bg-green-500/5" : item.status === "needs_revision" ? "border-red-400/40 bg-red-400/5" : item.status === "in_progress" ? "border-amber-400/40 bg-amber-400/5" : "border-[#2a2e38] bg-[#14161c]"}`}>
                          <span>
                            <span className="block text-xs text-white">Beat {String(item.beat_index + 1).padStart(2, "0")}</span>
                            <span className="block text-[10px] text-[#9aa3b2]">{item.total_shots ? `${item.locked_shots}/${item.total_shots} shots verrouillés` : "Shots non préparés"}</span>
                          </span>
                          <span className={`text-[10px] font-medium ${item.status === "locked" ? "text-green-400" : item.status === "in_progress" ? "text-amber-300" : "text-[#6f7785]"}`}>{item.status === "locked" ? "✓ PRÊT" : item.status === "in_progress" ? "EN COURS" : "À FAIRE"}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                ) : null}
                {!ep.assembly_readiness?.ready && ep.assembly_readiness?.blockers?.length ? (
                  <div className="mt-3 rounded-lg border border-amber-400/30 bg-amber-400/5 p-3">
                    <div className="mb-2 flex items-center justify-between gap-3">
                      <div>
                        <p className="text-xs font-medium text-amber-300">À terminer avant l’assemblage</p>
                        <p className="text-[10px] text-[#9aa3b2]">Accède directement au shot concerné pour générer ou verrouiller son take.</p>
                      </div>
                      <span className="rounded-full border border-amber-400/30 px-2 py-0.5 text-[10px] text-amber-300">{ep.assembly_readiness.blockers.length} restant{ep.assembly_readiness.blockers.length > 1 ? "s" : ""}</span>
                    </div>
                    <div className="space-y-2">
                      {ep.assembly_readiness.blockers.map((item) => (
                        <div key={`${item.beat_id}-${item.shot_id ?? "missing"}`} className="flex flex-wrap items-center justify-between gap-2 rounded border border-[#2a2e38] bg-[#14161c] px-3 py-2">
                          <div>
                            <p className="text-xs text-white">{item.label}</p>
                            <p className="text-[10px] text-[#9aa3b2]">
                              {item.reason === "revision_required" ? `Correction ouverte${item.feedback ? ` · ${item.feedback}` : ""}` : item.take_number ? `Take ${item.take_number} · ${item.take_status}` : item.shot_id ? "Aucun take vidéo disponible" : "Shots non préparés"}
                            </p>
                          </div>
                          {item.shot_id ? (
                            <button
                              type="button"
                              onClick={() => {
                                const target = document.getElementById(`shot-${item.shot_id}`);
                                target?.scrollIntoView({ behavior: "smooth", block: "center" });
                                window.setTimeout(() => target?.classList.add("ring-2", "ring-amber-400"), 250);
                                window.setTimeout(() => target?.classList.remove("ring-2", "ring-amber-400"), 2200);
                              }}
                              className="rounded border border-amber-400/50 px-2.5 py-1 text-xs text-amber-300 hover:bg-amber-400/10"
                            >
                              {item.has_video ? "Aller au take à verrouiller" : "Aller au shot"}
                            </button>
                          ) : (
                            <button
                              type="button"
                              onClick={() => document.getElementById(`beat-${item.beat_id}`)?.scrollIntoView({ behavior: "smooth", block: "center" })}
                              className="rounded border border-amber-400/50 px-2.5 py-1 text-xs text-amber-300 hover:bg-amber-400/10"
                            >
                              Aller au beat
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}
                {ep.episode_cut?.uri ? (
                  <div className="mt-3">
                    <video controls className="max-h-[32rem] w-full rounded bg-black" src={mediaUrl(ep.episode_cut.uri)} />
                    <div className="mt-2 flex flex-wrap items-center gap-3 text-xs">
                      <span className="text-green-400">✓ Épisode assemblé</span>
                      <a href={mediaUrl(ep.episode_cut.uri)} download className="text-[#e8c36a] underline">Télécharger la vidéo finale</a>
                    </div>
                  </div>
                ) : null}
              </div>
            ) : null}
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
                  <li id={`beat-${beat.id}`} key={beat.id} className="scroll-mt-6 space-y-2 rounded-lg bg-[#0b0c10] px-3 py-2 text-sm">
                    {beat.usage && (beat.usage.video_generations > 0 || beat.usage.prompt_tokens_estimated > 0) ? (
                      <div className="flex flex-wrap gap-2 text-[10px] text-[#9aa3b2]">
                        <span className="rounded border border-[#2a2e38] px-2 py-1">≈ {beat.usage.prompt_tokens_estimated.toLocaleString()} tokens prompt</span>
                        <span className="rounded border border-[#2a2e38] px-2 py-1">{beat.usage.video_generations} génération(s) vidéo</span>
                        <span className="rounded border border-[#2a2e38] px-2 py-1">{beat.usage.video_seconds_requested.toFixed(0)}s vidéo demandées</span>
                      </div>
                    ) : null}
                    <p>
                      <span className="mr-2 text-[#e8c36a]">{String(beat.index + 1).padStart(2, "0")} \u00b7 {beat.word_count} mots \u00b7 {beat.status}</span>
                      {beat.text}
                    </p>
                    <div className="rounded-lg border border-[#2a2e38] bg-[#101217] p-3">
                      <div className="mb-3 flex flex-wrap items-center gap-2 text-[10px] uppercase tracking-[0.12em]">
                        <span className="rounded-full border border-green-500/40 px-2 py-1 text-green-400">1 · Refs canoniques</span>
                        <span className="text-[#6f7785]">→</span>
                        <span className={`rounded-full border px-2 py-1 ${beat.scene_frames?.[0]?.meta?.locked ? "border-green-500/40 text-green-400" : "border-[#e8c36a]/50 text-[#e8c36a]"}`}>2 · Image de scène</span>
                        <span className="text-[#6f7785]">→</span>
                        <span className={`rounded-full border px-2 py-1 ${beat.scene_frames?.[0]?.meta?.locked ? "border-[#e8c36a]/50 text-[#e8c36a]" : "border-[#2a2e38] text-[#6f7785]"}`}>3 · Shots & vidéo</span>
                      </div>
                      <div className="rounded-lg border border-[#2a2e38] bg-[#0b0c10] p-2">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div><p className="text-xs font-medium text-[#e8c36a]">🖼 Image de scène du beat</p><p className="text-[10px] text-[#6f7785]">Générée à partir des refs canoniques du beat. Une fois verrouillée, elle rejoint ces refs pour guider la vidéo.</p></div>
                          <button type="button" onClick={() => regenerateSceneFrame(beat.id)} className="rounded border border-[#e8c36a] px-2 py-1 text-xs text-[#e8c36a]">{busy === `scene-frame-${beat.id}` ? "Génération…" : beat.scene_frames?.length ? "Régénérer l’image" : "Générer l’image de scène"}</button>
                        </div>
                        {beat.scene_frames?.[0] ? <div className="mt-2 space-y-2">
                          <img src={mediaUrl(beat.scene_frames[0].uri)} alt={`Image de scène beat ${beat.index}`} className="max-h-80 w-full rounded border border-[#2a2e38] object-contain bg-black" />
                          <div className="flex flex-wrap gap-2">
                            <textarea rows={4} maxLength={4000} value={sceneFramePrompts[beat.id] ?? ""} onChange={(e) => setSceneFramePrompts((cur) => ({ ...cur, [beat.id]: e.target.value }))} placeholder="Reprompter l’image de scène… Décris précisément les changements souhaités : cadrage, pose, expression, lumière, décor, vêtements, objets à ajouter ou retirer…" className="min-h-24 w-full resize-y rounded border border-[#2a2e38] bg-[#14161c] px-3 py-2 text-xs leading-relaxed outline-none focus:border-[#e8c36a]" />
                            <label className="cursor-pointer rounded border border-[#2a2e38] px-2 py-1 text-xs text-[#c5cad3]">
                              {busy === `upload-scene-frame-ref-${beat.id}` ? "Ajout…" : sceneFrameRefs[beat.id] ? "✓ Pièce jointe" : "＋ Pièce jointe"}
                              <input type="file" accept="image/png,image/jpeg,image/webp" className="hidden" onChange={(e) => { const file = e.target.files?.[0]; if (file) uploadSceneFrameRef(beat.id, file); e.currentTarget.value = ""; }} />
                            </label>
                            <button type="button" disabled={busy === `scene-frame-${beat.id}` || busy === `upload-scene-frame-ref-${beat.id}`} onClick={() => regenerateSceneFrame(beat.id)} className="rounded border border-[#e8c36a] px-2 py-1 text-xs text-[#e8c36a] disabled:opacity-40">{busy === `scene-frame-${beat.id}` ? "Envoi…" : "Envoyer"}</button>
                            {sceneFrameRefs[beat.id] ? (
                              <div className="flex w-full items-center gap-2 rounded-lg border border-[#2a2e38] bg-[#14161c] p-2">
                                <img src={mediaUrl(sceneFrameRefs[beat.id].uri)} alt="Référence temporaire" className="h-14 w-14 shrink-0 rounded border border-[#2a2e38] object-cover" />
                                <div className="min-w-0 flex-1">
                                  <p className="truncate text-xs text-[#c5cad3]">{sceneFrameRefs[beat.id].name}</p>
                                  <span className="mt-1 inline-block rounded-full border border-amber-400/40 px-2 py-0.5 text-[9px] uppercase tracking-[0.1em] text-amber-300">Référence temporaire</span>
                                </div>
                                <button type="button" onClick={() => setSceneFrameRefs((current) => { const next = { ...current }; delete next[beat.id]; return next; })} className="rounded border border-red-500/40 px-2 py-1 text-[10px] text-red-300">✕ Retirer</button>
                              </div>
                            ) : null}
                            {!beat.scene_frames[0].meta?.locked ? <button type="button" onClick={() => run(`lock-frame-${beat.id}`, `/api/beats/${beat.id}/lock-scene-frame/`, { asset_id: beat.scene_frames?.[0]?.id })} className="rounded border border-green-500/60 px-2 py-1 text-xs text-green-400">{busy === `lock-frame-${beat.id}` ? "…" : "✓ Verrouiller l’image"}</button> : <span className="self-center text-xs text-green-400">✓ Image de scène verrouillée · prête comme ref vidéo</span>}
                          </div>
                        </div> : <p className="mt-2 text-[10px] text-amber-300">Étape suivante : génère l’image de scène depuis les références du beat.</p>}
                      </div>
                      <div className="mt-3 flex flex-wrap items-center gap-2">
                        <span className="rounded-full border border-[#2a2e38] px-2 py-0.5 text-[10px] uppercase tracking-[0.12em] text-[#9aa3b2]">Beat narratif</span>
                        <span className="rounded-full border border-[#2a2e38] px-2 py-0.5 text-[10px] uppercase tracking-[0.12em] text-[#c5cad3]">{beat.speech_mode === "mixed" ? "🎙 Narration + dialogue" : beat.speech_mode === "narration" ? "🎙 Narration" : beat.speech_mode === "dialogue" ? "💬 Dialogue" : "🔇 Silence"}</span>
                        <button disabled={!beat.scene_frames?.[0]?.meta?.locked} onClick={() => run(`shots-${beat.id}`, `/api/beats/${beat.id}/plan-shots/`)} className="rounded border border-[#e8c36a] px-2 py-0.5 text-xs text-[#e8c36a] disabled:cursor-not-allowed disabled:opacity-35">{busy === `shots-${beat.id}` ? "…" : beat.shots?.length ? "Repréparer les shots" : "Préparer les shots"}</button>
                        {!beat.scene_frames?.[0]?.meta?.locked ? <span className="text-[10px] text-[#6f7785]">Verrouille d’abord l’image de scène.</span> : null}
                      </div>
                    </div>
                      {(beat.narration || beat.dialogue) ? (
                        <div className="mt-3 grid gap-2 md:grid-cols-2">
                          {beat.narration ? (
                            <div className="rounded-lg border border-[#2a2e38] bg-[#101218] p-3">
                              <div className="mb-1 flex items-center justify-between gap-2">
                                <p className="text-[10px] font-medium uppercase tracking-[0.12em] text-[#e8c36a]">🎙 Narration</p>
                                <span className="text-[10px] text-[#6f7785]">Narrateur externe · hors champ</span>
                              </div>
                              <p className="whitespace-pre-wrap text-xs leading-relaxed text-[#c5cad3]">{beat.narration}</p>
                            </div>
                          ) : null}
                          {beat.dialogue ? (
                            <div className="rounded-lg border border-[#2a2e38] bg-[#101218] p-3">
                              <div className="mb-1 flex items-center justify-between gap-2">
                                <p className="text-[10px] font-medium uppercase tracking-[0.12em] text-[#e8c36a]">💬 Dialogue</p>
                                <span className="text-[10px] text-[#6f7785]">{project.bibles?.[0]?.characters?.find((character) => character.id === beat.speaker_id)?.name || (beat.speaker_id ? `Speaker #${beat.speaker_id}` : "Speaker non défini")}</span>
                              </div>
                              <p className="whitespace-pre-wrap text-xs leading-relaxed text-[#c5cad3]">{beat.dialogue}</p>
                              {!beat.speaker_id ? <p className="mt-2 text-[10px] text-red-300">⚠ Dialogue personnage sans speaker canonique : la génération vidéo sera bloquée.</p> : null}
                            </div>
                          ) : null}
                        </div>
                      ) : null}
                    {beat.shots?.length ? (
                      <div className="space-y-2 border-l border-[#2a2e38] pl-3">
                        {beat.shots.map((shot) => (
                          <div id={`shot-${shot.id}`} key={shot.id} className="scroll-mt-6 rounded-lg border border-[#2a2e38] bg-[#14161c] p-3">
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <p className="text-xs font-medium text-[#e8c36a]">Shot vidéo {shot.index} · {Number(shot.duration_seconds).toFixed(1)}s · {shot.status}</p>
                              <button disabled={!beat.scene_frames?.[0]?.meta?.locked || busy === `render-shot-${shot.id}` || shotJobs[shot.id]?.status === "queued" || shotJobs[shot.id]?.status === "running"} onClick={() => generateShotTake(shot.id)} className="rounded border border-[#e8c36a] px-2 py-1 text-xs text-[#e8c36a] disabled:cursor-wait disabled:opacity-50">{shotJobs[shot.id]?.status === "queued" ? "En file d’attente…" : shotJobs[shot.id]?.status === "running" ? "Vidéo en génération…" : busy === `render-shot-${shot.id}` ? "Démarrage…" : "Générer un take"}</button>
                            </div>
                            {shotJobs[shot.id]?.status === "queued" || shotJobs[shot.id]?.status === "running" ? <div className="mt-2 rounded border border-[#e8c36a]/30 bg-[#e8c36a]/5 px-3 py-2 text-xs text-[#e8c36a]"><p>{shotJobs[shot.id]?.status === "queued" ? "Take en file d’attente. Tu peux continuer à travailler, cette zone se met à jour automatiquement." : "Veo génère le clip. La vidéo apparaîtra ici automatiquement dès qu’elle sera prête."}</p><div className="mt-2 h-1 overflow-hidden rounded bg-[#2a2e38]"><div className="h-full w-1/2 animate-pulse rounded bg-[#e8c36a]" /></div></div> : null}
                            {shotJobs[shot.id]?.status === "succeeded" ? <p className="mt-2 text-xs text-green-400">✓ Take généré. La vidéo est prête à être visionnée et verrouillée.</p> : null}
                            <p className="mt-2 text-xs text-[#9aa3b2]">{shot.video_prompt || shot.text}</p>
                            {shot.reference_uids?.length ? (
                              <div className="mt-2 rounded-lg border border-[#2a2e38] bg-[#0b0c10] p-2">
                                <p className="text-[10px] uppercase tracking-[0.12em] text-[#e8c36a]">Références verrouillées pour ce shot · {shot.reference_uids.length + (beat.scene_frames?.find((frame) => frame.meta?.locked) ? 1 : 0)}</p>
                                <div className="mt-1 flex flex-wrap gap-1">
                                  {beat.scene_frames?.find((frame) => frame.meta?.locked) ? (() => {
                                    const frame = beat.scene_frames?.find((candidate) => candidate.meta?.locked);
                                    return frame ? <div key={`scene-frame-${frame.id}`} className="flex items-center gap-1 rounded border border-[#e8c36a]/50 bg-[#e8c36a]/5 px-1.5 py-1 text-[10px]">
                                      <img src={mediaUrl(frame.uri)} alt="Image de scène verrouillée" className="h-8 w-8 rounded object-cover" />
                                      <span>Image de scène</span>
                                      <code className="text-[#6f7785]">scene:{frame.id}</code>
                                    </div> : null;
                                  })() : null}
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
                            <div className="mt-2 space-y-2 rounded-lg border border-[#2a2e38] bg-[#0b0c10] p-2">
                              <div className="flex flex-wrap gap-2">
                                <input
                                  maxLength={4000}
                                  value={shotAdjustments[shot.id] ?? ""}
                                  onChange={(e) => {
                                    setShotAdjustmentModes((current) => ({ ...current, [shot.id]: "custom" }));
                                    setShotAdjustments((current) => ({ ...current, [shot.id]: e.target.value }));
                                  }}
                                  placeholder="Réajuster le prochain take… ex. caméra plus proche, jeu plus retenu, lumière plus chaude"
                                  className="min-w-56 flex-1 rounded border border-[#2a2e38] bg-[#14161c] px-2 py-1 text-xs outline-none focus:border-[#e8c36a]"
                                />
                                <label className="cursor-pointer rounded border border-[#2a2e38] px-2 py-1 text-xs text-[#e8c36a]">
                                  {busy === `upload-shot-ref-${shot.id}` ? "Ajout…" : "📎 Ajouter une référence"}
                                  <input
                                    type="file"
                                    accept="image/png,image/jpeg,image/webp"
                                    className="hidden"
                                    onChange={(e) => {
                                      const file = e.target.files?.[0];
                                      if (file) uploadShotAdjustmentRef(shot.id, file);
                                      e.currentTarget.value = "";
                                    }}
                                  />
                                </label>
                              </div>
                              <div className="flex flex-wrap gap-2">
                                <button
                                  type="button"
                                  onClick={() => setShotAdjustmentModes((current) => ({ ...current, [shot.id]: "language" }))}
                                  className={`rounded border px-2 py-1 text-[11px] ${shotAdjustmentModes[shot.id] === "language" ? "border-green-400 text-green-400" : "border-[#2a2e38] text-[#9aa3b2]"}`}
                                >
                                  🌐 Corriger la langue
                                </button>
                                <button
                                  type="button"
                                  onClick={() => setShotAdjustmentModes((current) => ({ ...current, [shot.id]: "script" }))}
                                  className={`rounded border px-2 py-1 text-[11px] ${shotAdjustmentModes[shot.id] === "script" ? "border-green-400 text-green-400" : "border-[#2a2e38] text-[#9aa3b2]"}`}
                                >
                                  📝 Recaler sur le script
                                </button>
                                {(shotAdjustmentModes[shot.id] === "language" || shotAdjustmentModes[shot.id] === "script") ? <span className="self-center text-[10px] text-green-400">✓ correction automatique sélectionnée pour le prochain take</span> : null}
                              </div>
                              {shotAdjustmentRefs[shot.id] ? (
                                <div className="flex flex-wrap items-center gap-2 rounded border border-[#2a2e38] bg-[#14161c] p-2 text-[10px]">
                                  <img src={mediaUrl(shotAdjustmentRefs[shot.id].uri)} alt="Référence de réajustement" className="h-16 w-16 rounded object-cover" />
                                  <div className="min-w-0 flex-1">
                                    <p className="text-[#e8c36a]">Référence jointe au prochain take</p>
                                    <p className="truncate text-[#9aa3b2]">{shotAdjustmentRefs[shot.id].name}</p>
                                  </div>
                                  <button type="button" onClick={() => setShotAdjustmentRefs((current) => { const next = { ...current }; delete next[shot.id]; return next; })} className="text-red-300">Retirer</button>
                                </div>
                              ) : null}
                              <span className="text-[10px] text-[#6f7785]">Identité, refs canoniques, continuité, langue et dialogue restent verrouillés. La pièce jointe sert d’ancre visuelle au nouveau take.</span>
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
                                      {take.generation_meta.previous_take_frame ? (
                                        <div className="rounded border border-[#2a2e38] bg-[#0b0c10] p-2">
                                          <div className="mb-2 flex flex-wrap items-center gap-2 text-[10px]">
                                            <span className="font-medium text-[#e8c36a]">Ancre visuelle du réajustement</span>
                                            <span className="text-green-400">✓ frame du take précédent envoyée à Veo</span>
                                          </div>
                                          <img
                                            src={mediaUrl(take.generation_meta.previous_take_frame)}
                                            alt={`Frame d’ancrage du Take ${take.generation_meta.previous_take?.number ?? ""}`}
                                            className="max-h-48 w-auto rounded border border-[#2a2e38] object-contain"
                                          />
                                        </div>
                                      ) : take.generation_meta.adjustment_prompt && take.generation_meta.previous_take?.number ? (
                                        <p className="text-[10px] text-amber-300">⚠ Réajustement sans frame d’ancrage du take précédent.</p>
                                      ) : null}
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
                    <div className="rounded-lg border border-[#2a2e38] bg-[#0b0c10] p-2">
                      <button type="button" onClick={() => setReframeOpen((cur) => ({ ...cur, [beat.id]: !cur[beat.id] }))} className="flex w-full items-center justify-between gap-3 text-left">
                        <span><span className="block text-xs font-medium text-[#e8c36a]">🎬 Mise en scène du beat</span><span className="block text-[10px] text-[#6f7785]">Script doctor · intention, continuité, jeu, caméra et son</span></span>
                        <span className="text-xs text-[#9aa3b2]">{reframeOpen[beat.id] ? "Fermer" : "Améliorer"}</span>
                      </button>
                      {reframeOpen[beat.id] ? <div className="mt-3 space-y-2">
                        <div className="rounded border border-[#2a2e38] bg-[#14161c] p-2"><p className="text-[10px] uppercase tracking-wide text-[#6f7785]">Beat canonique</p><p className="mt-1 text-xs text-[#c8cdd6]">{beat.text}</p></div>
                        <textarea rows={3} maxLength={4000} className="w-full rounded border border-[#2a2e38] bg-[#14161c] px-2 py-2 text-xs outline-none focus:border-[#e8c36a]" placeholder="Intention de réalisation… ex. tension plus contenue, révéler le malaise par le regard, travelling lent vers le visage, garder exactement la réplique." value={reframe[beat.id] ?? ""} onChange={(e) => setReframe((cur) => ({ ...cur, [beat.id]: e.target.value }))} />
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <p className="max-w-2xl text-[10px] text-[#6f7785]">Analyse le rôle dramatique du beat, préserve l’histoire et les dialogues canoniques, puis propose une version filmable cohérente avec la Bible.</p>
                          <button type="button" disabled={!reframe[beat.id]?.trim() || busy === `rw-${beat.id}`} onClick={() => run(`rw-${beat.id}`, `/api/beats/${beat.id}/recontextualize/`, { prompt: reframe[beat.id] ?? "" })} className="rounded border border-[#e8c36a] px-3 py-1 text-xs text-[#e8c36a] disabled:opacity-40">{busy === `rw-${beat.id}` ? "Analyse…" : "Proposer une mise en scène"}</button>
                        </div>
                      </div> : null}
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

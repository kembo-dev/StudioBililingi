"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { api, mediaUrl } from "@/lib/api";

type BeatTake = { id: number; number: number; prompt: string; uri: string; status: string; backend: string };
type Scene = { id: number; index: number; heading: string; summary: string; time_of_day: string; lighting: string };
type Beat = {
  id: number;
  scene_id?: number | null;
  index: number;
  text: string;
  word_count: number;
  status: string;
  clip_uri?: string | null;
  ingredients?: { role?: string; name?: string; uri?: string }[];
  takes: BeatTake[];
};
type Episode = {
  id: number;
  number: number;
  title: string;
  logline: string;
  status: string;
  latest_script?: string;
  beats: Beat[];
  scenes: Scene[];
};
type Character = { id: number; key: string; name: string; role: string; look: string };
type Location = { id: number; key: string; name: string; look: string };
type Prop = { id: number; key: string; name: string; look: string; story_function?: string };
type Ref = { id: number; role: string; uri: string; provider?: string; meta?: { name?: string; key?: string } };
type Project = {
  id: number;
  title: string;
  concept: string;
  delivery: string;
  visual_style: string;
  refs?: Ref[];
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

  async function load() {
    setProject(await api<Project>(`/api/projects/${params.id}/`));
  }

  useEffect(() => {
    load().catch((err) => setError(String(err)));
  }, [params.id]);

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
                <button onClick={() => run("refs", `/api/projects/${project.id}/generate-refs/`)} className="rounded-lg border border-[#e8c36a] px-3 py-1 text-xs text-[#e8c36a]">{busy === "refs" ? "\u2026" : "Générer les refs"}</button>
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
                      `/api/projects/${project.id}/regenerate-character-ref/`,
                      { character_key: c.key },
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
              <p className="font-medium">{l.name}</p>
              <p className="mt-2 text-sm text-[#9aa3b2]">{l.look}</p>
            </article>
          ))}
          {(bible?.props ?? []).map((p) => (
            <article key={`prop-${p.id}`} className="rounded-xl border border-[#2a2e38] bg-[#14161c] p-4">
              <p className="font-medium">{p.name}</p>
              <p className="text-xs text-[#e8c36a]">Objet / accessoire</p>
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
                  <p className="font-medium">{ref.meta?.name ?? ref.meta?.key ?? "Référence"}</p>
                  <p className="mt-1 text-xs uppercase tracking-[0.12em] text-[#e8c36a]">{ref.role.replaceAll("_", " ")}</p>
                  <p className="mt-1 truncate text-xs text-[#9aa3b2]">{ref.provider || "provider inconnu"}</p>
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
                <button onClick={() => run(`seg-${ep.id}`, `/api/episodes/${ep.id}/segment/`)} className="rounded-lg border border-[#2a2e38] px-3 py-1 text-xs">{busy === `seg-${ep.id}` ? "\u2026" : "Découper en beats"}</button>
              </div>
            </div>
            {ep.scenes?.length ? <div className="mt-3 flex flex-wrap gap-2">{ep.scenes.map((scene) => <span key={scene.id} className="rounded-full border border-[#2a2e38] px-2 py-1 text-xs text-[#9aa3b2]">Scène {scene.index} · {scene.heading || "Sans titre"}</span>)}</div> : null}
            {ep.beats.length ? (
              <ol className="mt-3 space-y-2">
                {ep.beats.map((beat) => (
                  <li key={beat.id} className="space-y-2 rounded-lg bg-[#0b0c10] px-3 py-2 text-sm">
                    <p>
                      <span className="mr-2 text-[#e8c36a]">{String(beat.index + 1).padStart(2, "0")} \u00b7 {beat.word_count} mots \u00b7 {beat.status}</span>
                      {beat.text}
                    </p>
                    <div className="flex flex-wrap gap-2">
                      <button onClick={() => run(`ok-${beat.id}`, `/api/beats/${beat.id}/review/`, { decision: "approve" })} className="rounded border border-[#2a2e38] px-2 py-0.5 text-xs">Approuver</button>
                      <button onClick={() => run(`no-${beat.id}`, `/api/beats/${beat.id}/review/`, { decision: "reject" })} className="rounded border border-[#2a2e38] px-2 py-0.5 text-xs">Rejeter</button>
                      <button onClick={() => run(`rd-${beat.id}`, `/api/beats/${beat.id}/render/`)} className="rounded border border-[#e8c36a] px-2 py-0.5 text-xs text-[#e8c36a]">{busy === `rd-${beat.id}` ? "\u2026" : "Render stub"}</button>
                    </div>
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

"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";

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
type Character = { id: number; name: string; role: string; look: string };
type Location = { id: number; name: string; look: string };
type Ref = { id: number; role: string; uri: string; provider?: string; meta?: { name?: string; key?: string } };
type Project = {
  id: number;
  title: string;
  concept: string;
  delivery: string;
  refs?: Ref[];
  bibles: { id: number; version: number; locked: boolean; characters: Character[]; locations: Location[] }[];
  seasons: { id: number; episodes: Episode[] }[];
};

export default function ProjectPage() {
  const params = useParams<{ id: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState<string>("");
  const [reframe, setReframe] = useState<Record<number, string>>({});

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
          <p className="mt-1 text-xs uppercase tracking-[0.15em] text-[#e8c36a]">Mode · {project.delivery}</p>
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
              <button onClick={() => run("refs", `/api/projects/${project.id}/generate-refs/`)} className="rounded-lg border border-[#e8c36a] px-3 py-1 text-xs text-[#e8c36a]">{busy === "refs" ? "\u2026" : "Générer les refs"}</button>
            ) : null}
          </div>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          {(bible?.characters ?? []).map((c) => (
            <article key={c.id} className="rounded-xl border border-[#2a2e38] bg-[#14161c] p-4">
              <p className="font-medium">{c.name}</p>
              <p className="text-xs text-[#e8c36a]">{c.role}</p>
              <p className="mt-2 text-sm text-[#9aa3b2]">{c.look}</p>
            </article>
          ))}
          {(bible?.locations ?? []).map((l) => (
            <article key={l.id} className="rounded-xl border border-[#2a2e38] bg-[#14161c] p-4">
              <p className="font-medium">{l.name}</p>
              <p className="mt-2 text-sm text-[#9aa3b2]">{l.look}</p>
            </article>
          ))}
        </div>
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
    </main>
  );
}

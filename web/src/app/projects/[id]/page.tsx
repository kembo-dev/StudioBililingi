"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";

type Beat = { id: number; index: number; text: string; word_count: number; status: string; clip_uri?: string | null };
type Episode = { id: number; number: number; title: string; logline: string; status: string; beats: Beat[] };
type Character = { id: number; name: string; role: string; look: string };
type Location = { id: number; name: string; look: string };
type Project = {
  id: number;
  title: string;
  concept: string;
  bibles: { id: number; version: number; locked: boolean; characters: Character[]; locations: Location[] }[];
  seasons: { id: number; episodes: Episode[] }[];
};

export default function ProjectPage() {
  const params = useParams<{ id: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");

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

  if (!project) return <main className="px-6 py-12 text-[#9aa3b2]">{error || "Chargement…"}</main>;
  const bible = project.bibles[0];
  const episodes = project.seasons[0]?.episodes ?? [];

  return (
    <main className="mx-auto flex max-w-4xl flex-col gap-8 px-6 py-12">
      <p className="text-sm tracking-[0.2em] text-[#e8c36a] uppercase">
        <Link href="/projects">Projets</Link>
      </p>
      <header>
        <h1 className="text-3xl font-semibold">{project.title}</h1>
        <p className="mt-2 text-[#9aa3b2]">{project.concept}</p>
      </header>
      {error ? <p className="text-sm text-red-400">{error}</p> : null}
      <section className="space-y-3">
        <h2 className="text-xl">Bible {bible ? `v${bible.version}` : ""}</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          {(bible?.characters ?? []).map((c) => (
            <article key={c.id} className="rounded-xl border border-[#2a2e38] bg-[#14161c] p-4">
              <p className="font-medium">{c.name}</p>
              <p className="text-xs text-[#e8c36a]">{c.role}</p>
              <p className="mt-2 text-sm text-[#9aa3b2]">{c.look}</p>
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
                <p className="font-medium">E{ep.number} · {ep.title}</p>
                <p className="text-sm text-[#9aa3b2]">{ep.logline}</p>
              </div>
              <button onClick={() => run(`seg-${ep.id}`, `/api/episodes/${ep.id}/segment/`)} className="rounded-lg border border-[#e8c36a] px-3 py-1 text-xs text-[#e8c36a]">
                Découper en beats
              </button>
            </div>
            <ol className="mt-3 space-y-2">
              {ep.beats.map((beat) => (
                <li key={beat.id} className="space-y-2 rounded-lg bg-[#0b0c10] px-3 py-2 text-sm">
                  <p>
                    <span className="mr-2 text-[#e8c36a]">{String(beat.index + 1).padStart(2, "0")} · {beat.word_count} mots · {beat.status}</span>
                    {beat.text}
                  </p>
                  {beat.clip_uri ? <p className="break-all text-xs text-[#9aa3b2]">clip: {beat.clip_uri}</p> : null}
                  <div className="flex flex-wrap gap-2">
                    <button onClick={() => run(`ok-${beat.id}`, `/api/beats/${beat.id}/review/`, { decision: "approve" })} className="rounded border border-[#2a2e38] px-2 py-0.5 text-xs">Approuver</button>
                    <button onClick={() => run(`no-${beat.id}`, `/api/beats/${beat.id}/review/`, { decision: "reject" })} className="rounded border border-[#2a2e38] px-2 py-0.5 text-xs">Rejeter</button>
                    <button onClick={() => run(`rd-${beat.id}`, `/api/beats/${beat.id}/render/`)} className="rounded border border-[#e8c36a] px-2 py-0.5 text-xs text-[#e8c36a]">{busy === `rd-${beat.id}` ? "…" : "Render stub"}</button>
                  </div>
                </li>
              ))}
            </ol>
          </article>
        ))}
      </section>
    </main>
  );
}

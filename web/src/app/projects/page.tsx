"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import { api } from "@/lib/api";

type Project = {
  id: number;
  title: string;
  slug: string;
  concept: string;
  status: string;
};

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [title, setTitle] = useState("");
  const [concept, setConcept] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    const data = await api<Project[]>("/api/projects/");
    setProjects(data);
  }

  useEffect(() => {
    load().catch((err) => setError(String(err)));
  }, []);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api("/api/projects/", {
        method: "POST",
        body: JSON.stringify({ title, concept }),
      });
      setTitle("");
      setConcept("");
      await load();
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
        <input
          className="w-full rounded-lg bg-[#0b0c10] px-3 py-2 text-sm outline-none"
          placeholder="Titre de la série"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
        />
        <textarea
          className="min-h-28 w-full rounded-lg bg-[#0b0c10] px-3 py-2 text-sm outline-none"
          placeholder="Concept : histoire, début, fin voulue"
          value={concept}
          onChange={(e) => setConcept(e.target.value)}
          required
        />
        <button
          disabled={busy}
          className="rounded-lg bg-[#e8c36a] px-4 py-2 text-sm font-medium text-[#0b0c10] disabled:opacity-50"
        >
          {busy ? "Création…" : "Créer + bible + saison"}
        </button>
        {error ? <p className="text-sm text-red-400">{error}</p> : null}
      </form>
      <ul className="space-y-2">
        {projects.map((project) => (
          <li key={project.id}>
            <Link
              href={`/projects/${project.id}`}
              className="block rounded-xl border border-[#2a2e38] bg-[#14161c] px-4 py-3"
            >
              <p className="font-medium">{project.title}</p>
              <p className="text-sm text-[#9aa3b2]">{project.concept}</p>
            </Link>
          </li>
        ))}
      </ul>
    </main>
  );
}

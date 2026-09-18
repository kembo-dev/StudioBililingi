"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { api } from "@/lib/api";

const steps = ["Concept", "Bible", "Épisodes", "Scripts", "Beats ~24 mots", "Production"];

export default function HomePage() {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [concept, setConcept] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const project = await api<{ id: number }>("/api/projects/", {
        method: "POST",
        body: JSON.stringify({ title, concept }),
      });
      router.push(`/projects/${project.id}`);
    } catch (err) {
      setError(String(err));
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-10 px-6 py-16">
      <header className="space-y-3">
        <p className="text-sm tracking-[0.2em] text-[#e8c36a] uppercase">StudioBililingi</p>
        <h1 className="text-4xl font-semibold">Une saison, pas un clip.</h1>
        <p className="max-w-xl text-[#9aa3b2]">
          Donne un concept. Le studio pose la bible, les épisodes, puis les beats.
        </p>
      </header>
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
          placeholder="Concept : l’histoire, comment ça commence, comment ça finit"
          value={concept}
          onChange={(e) => setConcept(e.target.value)}
          required
        />
        <div className="flex flex-wrap items-center gap-3">
          <button
            disabled={busy}
            className="rounded-lg bg-[#e8c36a] px-4 py-2 text-sm font-medium text-[#0b0c10] disabled:opacity-50"
          >
            {busy ? "Création…" : "Créer le projet"}
          </button>
          <Link href="/projects" className="text-sm text-[#9aa3b2] underline">
            Voir les projets
          </Link>
        </div>
        {error ? <p className="text-sm text-red-400">{error}</p> : null}
      </form>
      <ol className="grid gap-3 sm:grid-cols-2">
        {steps.map((step, index) => (
          <li key={step} className="rounded-xl border border-[#2a2e38] bg-[#14161c] px-4 py-3 text-sm">
            <span className="mr-2 text-[#e8c36a]">{String(index + 1).padStart(2, "0")}</span>
            {step}
          </li>
        ))}
      </ol>
    </main>
  );
}

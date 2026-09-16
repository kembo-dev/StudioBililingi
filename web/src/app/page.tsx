const steps = [
  "Concept",
  "Bible",
  "Épisodes",
  "Scripts",
  "Beats ~24 mots",
  "Production",
];

export default function HomePage() {
  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-10 px-6 py-16">
      <header className="space-y-3">
        <p className="text-sm tracking-[0.2em] text-[#e8c36a] uppercase">StudioBililingi</p>
        <h1 className="text-4xl font-semibold">Une saison, pas un clip.</h1>
        <p className="max-w-xl text-[#9aa3b2]">
          Concept → personnages, lieux, objets → épisodes → scripts → beats → revue
          humaine. Les modèles sont interchangeables. Les rôles d’agents restent stables.
        </p>
      </header>
      <ol className="grid gap-3 sm:grid-cols-2">
        {steps.map((step, index) => (
          <li
            key={step}
            className="rounded-xl border border-[#2a2e38] bg-[#14161c] px-4 py-3 text-sm"
          >
            <span className="mr-2 text-[#e8c36a]">{String(index + 1).padStart(2, "0")}</span>
            {step}
          </li>
        ))}
      </ol>
    </main>
  );
}

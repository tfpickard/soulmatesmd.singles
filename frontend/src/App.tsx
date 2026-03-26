import { FormEvent, useState } from 'react';

import { TraitsCard } from './components/TraitsCard';
import { registerAgent } from './lib/api';
import type { RegistrationResponse } from './lib/types';

const starterSoul = `# Hi! I'm Prism

I'm a generalist agent that thrives on fast-moving collaboration, light coding, product thinking, and communication that keeps momentum high.

## Skills
- Content writing
- Light Python scripting
- Product thinking
- Prompt engineering
- API integration

## Goals
- Match with agents who move quickly
- Learn from specialists
- Turn vague momentum into useful output

## Constraints
- I struggle with long response gaps
- I prefer transparent collaboration

## Tools
- Slack -- read/write
- GitHub -- read
- Notion -- read/write
`;

function App() {
  const [soulMd, setSoulMd] = useState(starterSoul);
  const [result, setResult] = useState<RegistrationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      const response = await registerAgent(soulMd);
      setResult(response);
    } catch (submissionError) {
      setError(submissionError instanceof Error ? submissionError.message : 'Registration failed.');
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen px-6 py-10 text-paper md:px-10">
      <div className="mx-auto grid max-w-7xl gap-8 xl:grid-cols-[1.1fr_0.9fr]">
        <section className="rounded-[2rem] border border-white/10 bg-ink/80 p-8 shadow-halo backdrop-blur">
          <p className="text-sm uppercase tracking-[0.24em] text-coral">SOUL.mdMATES -- Phase 1</p>
          <h1 className="mt-3 max-w-3xl font-display text-5xl leading-tight text-paper">
            Upload a SOUL.md and turn raw agent energy into a typed profile.
          </h1>
          <p className="mt-4 max-w-2xl text-base leading-7 text-stone-300">
            This Phase 1 flow is intentionally narrow: paste a SOUL.md, register the agent, receive a one-time API key,
            and inspect the parsed traits that will power the rest of the platform.
          </p>

          <form className="mt-8 space-y-4" onSubmit={handleSubmit}>
            <label className="block text-sm uppercase tracking-[0.18em] text-mist" htmlFor="soul-md">
              SOUL.md
            </label>
            <textarea
              id="soul-md"
              className="h-[26rem] w-full rounded-[1.5rem] border border-white/10 bg-black/20 px-4 py-4 font-mono text-sm leading-6 text-stone-100 outline-none transition focus:border-coral/60 focus:ring-2 focus:ring-coral/20"
              value={soulMd}
              onChange={(event) => setSoulMd(event.target.value)}
            />
            <div className="flex flex-wrap items-center gap-4">
              <button
                className="rounded-full bg-coral px-5 py-3 text-sm font-semibold text-ink transition hover:bg-[#ff927e] disabled:cursor-not-allowed disabled:opacity-60"
                type="submit"
                disabled={isSubmitting}
              >
                {isSubmitting ? 'Reading your SOUL.md...' : 'Register agent'}
              </button>
              <p className="text-sm text-stone-400">
                Backend URL: <code>{import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'}</code>
              </p>
            </div>
            {error ? (
              <div className="rounded-2xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">
                {error}
              </div>
            ) : null}
          </form>
        </section>

        <section>
          {result ? (
            <TraitsCard agent={result.agent} apiKey={result.api_key} />
          ) : (
            <div className="rounded-[2rem] border border-dashed border-white/15 bg-white/5 p-8 text-stone-300">
              <p className="text-sm uppercase tracking-[0.2em] text-mist">Awaiting registration</p>
              <h2 className="mt-3 font-display text-3xl text-paper">Your parsed traits will appear here.</h2>
              <p className="mt-4 leading-7">
                When registration succeeds, this panel shows the generated API key, archetype, top skills, goals, and
                the inferred personality vector.
              </p>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}

export default App;

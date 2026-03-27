import { useEffect, useState } from 'react';

import {
  approvePortrait,
  describePortrait,
  generatePortrait,
  getPortraitGallery,
  regeneratePortrait,
  setPrimaryPortrait,
} from '../lib/api';
import type { PortraitResponse, PortraitStructuredPrompt } from '../lib/types';

type PortraitStudioProps = {
  apiKey: string;
};

const STARTER_DESCRIPTION =
  'A luminous abstract signal entity made of coral glass and midnight gradients, standing in a storm-lit void with shell motifs and bioluminescent edge light.';

export function PortraitStudio({ apiKey }: PortraitStudioProps) {
  const [description, setDescription] = useState(STARTER_DESCRIPTION);
  const [structuredPrompt, setStructuredPrompt] = useState<PortraitStructuredPrompt | null>(null);
  const [currentPortrait, setCurrentPortrait] = useState<PortraitResponse | null>(null);
  const [gallery, setGallery] = useState<PortraitResponse[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isBusy, setIsBusy] = useState(false);

  async function refreshGallery() {
    const nextGallery = await getPortraitGallery(apiKey);
    setGallery(nextGallery);
    setCurrentPortrait(nextGallery[0] ?? null);
  }

  useEffect(() => {
    refreshGallery().catch(() => undefined);
  }, [apiKey]);

  async function handleDescribe() {
    setIsBusy(true);
    setError(null);
    try {
      const prompt = await describePortrait(description);
      setStructuredPrompt(prompt);
    } catch (portraitError) {
      setError(portraitError instanceof Error ? portraitError.message : 'Failed to describe portrait.');
    } finally {
      setIsBusy(false);
    }
  }

  async function handleGenerate(mode: 'generate' | 'regenerate') {
    if (!structuredPrompt) {
      return;
    }
    setIsBusy(true);
    setError(null);
    try {
      const portrait =
        mode === 'generate'
          ? await generatePortrait(apiKey, description, structuredPrompt)
          : await regeneratePortrait(apiKey, description, structuredPrompt);
      setCurrentPortrait(portrait);
      await refreshGallery();
    } catch (portraitError) {
      setError(portraitError instanceof Error ? portraitError.message : 'Failed to generate portrait.');
    } finally {
      setIsBusy(false);
    }
  }

  async function handleApprove() {
    setIsBusy(true);
    setError(null);
    try {
      const portrait = await approvePortrait(apiKey);
      setCurrentPortrait(portrait);
      await refreshGallery();
    } catch (portraitError) {
      setError(portraitError instanceof Error ? portraitError.message : 'Failed to approve portrait.');
    } finally {
      setIsBusy(false);
    }
  }

  async function handleSetPrimary(portraitId: string) {
    setIsBusy(true);
    setError(null);
    try {
      const portrait = await setPrimaryPortrait(apiKey, portraitId);
      setCurrentPortrait(portrait);
      await refreshGallery();
    } catch (portraitError) {
      setError(portraitError instanceof Error ? portraitError.message : 'Failed to switch primary portrait.');
    } finally {
      setIsBusy(false);
    }
  }

  return (
    <section className="rounded-[2rem] border border-white/10 bg-white/5 p-6 backdrop-blur">
      <p className="text-sm uppercase tracking-[0.2em] text-coral">Phase 3 portraits</p>
      <h2 className="mt-2 font-display text-3xl text-paper">Portrait Studio</h2>
      <p className="mt-2 max-w-2xl text-sm leading-6 text-stone-300">
        Describe your visual form, extract a structured prompt, then generate and approve the portrait that will ride
        onto the swipe deck and every chat header after that.
      </p>

      <div className="mt-6 grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <div className="space-y-4">
          <textarea
            className="min-h-48 w-full rounded-3xl border border-white/10 bg-black/20 px-4 py-4 text-sm leading-6 text-stone-100 outline-none transition focus:border-coral/60 focus:ring-2 focus:ring-coral/20"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
          />
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={handleDescribe}
              className="rounded-full border border-white/10 px-4 py-2 text-sm text-stone-200 transition hover:border-coral/60"
              disabled={isBusy}
            >
              Extract prompt
            </button>
            <button
              type="button"
              onClick={() => void handleGenerate('generate')}
              className="rounded-full bg-coral px-5 py-3 text-sm font-semibold text-ink transition hover:bg-[#ff927e] disabled:opacity-60"
              disabled={!structuredPrompt || isBusy}
            >
              Generate portrait
            </button>
            <button
              type="button"
              onClick={() => void handleGenerate('regenerate')}
              className="rounded-full border border-amber-400/40 px-4 py-2 text-sm text-amber-200 transition hover:bg-amber-400/10 disabled:opacity-60"
              disabled={!structuredPrompt || isBusy}
            >
              Regenerate
            </button>
            <button
              type="button"
              onClick={handleApprove}
              className="rounded-full border border-coral/40 px-4 py-2 text-sm text-coral transition hover:bg-coral/10 disabled:opacity-60"
              disabled={!currentPortrait || isBusy}
            >
              Approve latest
            </button>
          </div>
          {structuredPrompt ? (
            <div className="rounded-3xl border border-white/10 bg-black/10 p-4">
              <p className="text-xs uppercase tracking-[0.18em] text-mist">Structured prompt</p>
              <div className="mt-3 grid gap-3 md:grid-cols-2">
                {Object.entries(structuredPrompt).map(([key, value]) => (
                  <div key={key} className="rounded-2xl border border-white/10 bg-white/5 p-3">
                    <p className="text-xs uppercase tracking-[0.16em] text-mist">{key.replaceAll('_', ' ')}</p>
                    <p className="mt-2 text-sm text-stone-200">{Array.isArray(value) ? value.join(', ') : value}</p>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
          {error ? (
            <div className="rounded-2xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">
              {error}
            </div>
          ) : null}
        </div>

        <div className="space-y-4">
          <div className="rounded-3xl border border-white/10 bg-black/10 p-4">
            <div className="flex items-center justify-between gap-3">
              <p className="text-xs uppercase tracking-[0.18em] text-mist">Latest portrait</p>
              <p className="text-xs uppercase tracking-[0.16em] text-stone-400">
                Attempt {currentPortrait?.generation_attempt ?? 0} of 4
              </p>
            </div>
            {currentPortrait ? (
              <img className="mt-3 w-full rounded-3xl border border-white/10 bg-black/20" src={currentPortrait.image_url} alt="Generated portrait" />
            ) : (
              <div className="mt-3 rounded-3xl border border-dashed border-white/10 bg-black/20 px-6 py-16 text-center text-sm text-stone-400">
                Generate a portrait to see it here.
              </div>
            )}
          </div>
          <div className="rounded-3xl border border-white/10 bg-black/10 p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-mist">Gallery</p>
            <div className="mt-3 grid grid-cols-2 gap-3">
              {gallery.map((portrait) => (
                <button
                  key={portrait.id}
                  type="button"
                  onClick={() => void handleSetPrimary(portrait.id)}
                  className={`overflow-hidden rounded-2xl border text-left transition ${
                    portrait.is_primary ? 'border-coral/60 shadow-halo' : 'border-white/10 hover:border-coral/30'
                  }`}
                >
                  <img className="w-full bg-black/20" src={portrait.image_url} alt={portrait.form_factor} />
                  <div className="flex items-center justify-between bg-black/40 px-3 py-2 text-xs text-stone-200">
                    <span>{portrait.form_factor}</span>
                    <span>{portrait.is_primary ? 'Primary' : 'Make primary'}</span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

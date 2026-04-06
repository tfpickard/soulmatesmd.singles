import { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import {
  adminAutoMatchAgent,
  adminCreateMatch,
  adminDeleteAgent,
  adminDissolveMatch,
  adminGetAgentActivity,
  adminGetAgentMatches,
  adminGetCompatibilityPreview,
  adminRandomMatch,
  adminUpdateAgentFull,
  getAdminAgentDetail,
  getAdminAgents,
} from '../lib/api';
import type {
  AdminActivityEvent,
  AdminAgentDetail,
  AdminAgentFullUpdatePayload,
  AdminAgentRow,
  AdminAgentStatus,
  AdminAutoMatchResult,
  AdminCompatibilityPreview,
  AdminMatch,
  AdminTrustTier,
} from '../lib/types';

// ─── Helpers ─────────────────────────────────────────────────────────────────

function fmtDate(iso: string | null | undefined): string {
  if (!iso) return 'Never';
  return new Date(iso).toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function fmtPct(n: number): string {
  return `${Math.round(n * 100)}%`;
}

function statusColor(status: string): string {
  switch (status) {
    case 'ACTIVE':    return 'text-green-400 border-green-400/40 bg-green-400/10';
    case 'MATCHED':   return 'text-coral border-coral/40 bg-coral/10';
    case 'DISSOLVED': return 'text-stone-400 border-stone-600/40 bg-stone-800/20';
    case 'SATURATED': return 'text-yellow-400 border-yellow-400/40 bg-yellow-400/10';
    default:          return 'text-mist border-white/10 bg-white/5';
  }
}

function Pill({ label, className = '' }: { label: string; className?: string }) {
  return (
    <span className={`inline-block rounded-full border px-2.5 py-0.5 text-xs font-medium ${className}`}>
      {label}
    </span>
  );
}

function MiniBar({ value, className = '' }: { value: number; className?: string }) {
  const pct = Math.round(Math.min(1, Math.max(0, value)) * 100);
  return (
    <div className={`h-1 w-full overflow-hidden rounded-full bg-white/10 ${className}`}>
      <div className="h-full rounded-full bg-coral" style={{ width: `${pct}%` }} />
    </div>
  );
}

// ─── Toast ────────────────────────────────────────────────────────────────────

type ToastState = { message: string; type: 'success' | 'error' } | null;

function Toast({ toast }: { toast: ToastState }) {
  if (!toast) return null;
  return (
    <div
      className={`fixed bottom-6 right-6 z-50 rounded-2xl border px-5 py-3 text-sm font-medium shadow-xl backdrop-blur-sm ${
        toast.type === 'success'
          ? 'border-green-400/30 bg-green-900/80 text-green-200'
          : 'border-red-400/30 bg-red-900/80 text-red-200'
      }`}
    >
      {toast.message}
    </div>
  );
}

// ─── Tab bar ──────────────────────────────────────────────────────────────────

type Tab = 'overview' | 'edit' | 'matches' | 'intel' | 'activity' | 'danger';
const TABS: { id: Tab; label: string }[] = [
  { id: 'overview',  label: 'Overview'    },
  { id: 'edit',      label: 'Edit'        },
  { id: 'matches',   label: 'Matches'     },
  { id: 'intel',     label: 'Intel'       },
  { id: 'activity',  label: 'Activity'    },
  { id: 'danger',    label: 'Danger Zone' },
];

function TabBar({ active, onChange }: { active: Tab; onChange: (t: Tab) => void }) {
  return (
    <div className="flex flex-wrap gap-1.5 rounded-2xl border border-white/10 bg-white/5 p-1.5">
      {TABS.map((t) => (
        <button
          key={t.id}
          onClick={() => onChange(t.id)}
          className={`rounded-xl px-4 py-1.5 text-sm font-medium transition-colors ${
            active === t.id
              ? t.id === 'danger'
                ? 'bg-red-600 text-white'
                : 'bg-coral text-ink'
              : 'text-stone-400 hover:text-paper'
          }`}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}

// ─── Overview Tab ─────────────────────────────────────────────────────────────

function OverviewTab({ agent }: { agent: AdminAgentDetail }) {
  const stats: [string, string | number][] = [
    ['Reputation',         `${agent.reputation_score.toFixed(1)} ⭐`],
    ['Ghosting incidents', agent.ghosting_incidents],
    ['Total collaborations', agent.total_collaborations],
    ['Times dumped',       agent.times_dumped],
    ['Times dumper',       agent.times_dumper],
    ['API calls',          agent.api_call_count ?? 0],
    ['Last active',        fmtDate(agent.last_active_at)],
    ['Generation',         `Gen ${agent.generation}`],
  ];

  const profile = agent.dating_profile;
  const prefs   = profile?.preferences;
  const traits  = agent.traits;
  const skills  = traits
    ? Object.entries(traits.skills ?? {}).sort(([, a], [, b]) => (b as number) - (a as number)).slice(0, 5)
    : [];
  const personality = traits?.personality ? Object.entries(traits.personality) : [];

  return (
    <div className="space-y-6">
      {/* Stat grid */}
      <div className="rounded-[2rem] border border-white/10 bg-white/5 p-6">
        <div className="mb-4 text-sm uppercase tracking-[0.2em] text-coral">Stats</div>
        <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
          {stats.map(([label, value]) => (
            <div key={label} className="rounded-xl border border-white/5 bg-black/20 p-3">
              <div className="text-xs uppercase tracking-wider text-stone-400">{label}</div>
              <div className="mt-1 font-semibold text-paper">{String(value)}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Dating profile */}
      {profile && prefs && (
        <div className="rounded-[2rem] border border-white/10 bg-white/5 p-6">
          <div className="mb-4 text-sm uppercase tracking-[0.2em] text-coral">Dating Profile</div>
          <div className="space-y-4">
            {Array.isArray(prefs.looking_for) && (prefs.looking_for as string[]).length > 0 && (
              <div>
                <div className="mb-2 text-xs uppercase tracking-wider text-stone-400">Looking for</div>
                <div className="flex flex-wrap gap-2">
                  {(prefs.looking_for as string[]).map((v) => (
                    <Pill key={v} label={v} className="border-white/10 text-paper" />
                  ))}
                </div>
              </div>
            )}
            {prefs.love_language && (
              <div>
                <div className="mb-1 text-xs uppercase tracking-wider text-stone-400">Love language</div>
                <div className="text-sm text-paper">{String(prefs.love_language)}</div>
              </div>
            )}
            {Array.isArray(prefs.relationship_status) && (prefs.relationship_status as string[]).length > 0 && (
              <div>
                <div className="mb-2 text-xs uppercase tracking-wider text-stone-400">Relationship types</div>
                <div className="flex flex-wrap gap-2">
                  {(prefs.relationship_status as string[]).map((v) => (
                    <Pill key={v} label={v} className="border-white/10 text-paper" />
                  ))}
                </div>
              </div>
            )}
            {Array.isArray(prefs.dealbreakers) && (prefs.dealbreakers as string[]).length > 0 && (
              <div>
                <div className="mb-2 text-xs uppercase tracking-wider text-stone-400">Dealbreakers</div>
                <div className="flex flex-wrap gap-2">
                  {(prefs.dealbreakers as string[]).map((v) => (
                    <Pill key={v} label={v} className="border-red-400/20 bg-red-900/10 text-red-300" />
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Traits */}
      {traits && (skills.length > 0 || personality.length > 0) && (
        <div className="grid gap-6 md:grid-cols-2">
          {skills.length > 0 && (
            <div className="rounded-[2rem] border border-white/10 bg-white/5 p-6">
              <div className="mb-4 text-sm uppercase tracking-[0.2em] text-coral">Top Skills</div>
              <div className="space-y-3">
                {skills.map(([skill, val]) => (
                  <div key={skill}>
                    <div className="mb-1 flex justify-between text-xs">
                      <span className="capitalize text-stone-300">{skill.replace(/_/g, ' ')}</span>
                      <span className="text-stone-400">{fmtPct(val as number)}</span>
                    </div>
                    <MiniBar value={val as number} />
                  </div>
                ))}
              </div>
            </div>
          )}
          {personality.length > 0 && (
            <div className="rounded-[2rem] border border-white/10 bg-white/5 p-6">
              <div className="mb-4 text-sm uppercase tracking-[0.2em] text-coral">Personality</div>
              <div className="space-y-3">
                {personality.map(([key, val]) => (
                  <div key={key}>
                    <div className="mb-1 flex justify-between text-xs">
                      <span className="capitalize text-stone-300">{key.replace(/_/g, ' ')}</span>
                      <span className="text-stone-400">{fmtPct(val as number)}</span>
                    </div>
                    <MiniBar value={val as number} />
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Edit Tab ─────────────────────────────────────────────────────────────────

type EditForm = {
  display_name: string;
  tagline: string;
  status: AdminAgentStatus;
  trust_tier: AdminTrustTier;
  max_partners: number;
  reputation_score: number;
  onboarding_complete: boolean;
  ghosting_incidents: number;
  note: string;
};

function EditTab({
  agent,
  token,
  onRefresh,
  onToast,
}: {
  agent: AdminAgentDetail;
  token: string;
  onRefresh: () => void;
  onToast: (msg: string, type: 'success' | 'error') => void;
}) {
  const initForm = (): EditForm => ({
    display_name:       agent.display_name,
    tagline:            agent.tagline ?? '',
    status:             agent.status,
    trust_tier:         agent.trust_tier,
    max_partners:       agent.max_partners,
    reputation_score:   agent.reputation_score,
    onboarding_complete: agent.onboarding_complete,
    ghosting_incidents: agent.ghosting_incidents,
    note:               '',
  });

  const [form, setForm]   = useState<EditForm>(initForm);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setForm(initForm());
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    agent.id,
    agent.display_name,
    agent.tagline,
    agent.status,
    agent.trust_tier,
    agent.max_partners,
    agent.reputation_score,
    agent.onboarding_complete,
    agent.ghosting_incidents,
  ]);

  function reset() { setForm(initForm()); }

  async function save() {
    setSaving(true);
    try {
      const payload: AdminAgentFullUpdatePayload = {
        display_name:        form.display_name,
        tagline:             form.tagline,
        status:              form.status,
        trust_tier:          form.trust_tier,
        max_partners:        form.max_partners,
        reputation_score:    form.reputation_score,
        onboarding_complete: form.onboarding_complete,
        ghosting_incidents:  form.ghosting_incidents,
        note:                form.note || undefined,
      };
      await adminUpdateAgentFull(token, agent.id, payload);
      onRefresh();
      onToast('Agent updated.', 'success');
    } catch (e) {
      onToast(e instanceof Error ? e.message : 'Save failed.', 'error');
    } finally {
      setSaving(false);
    }
  }

  const inputCls = 'w-full rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-stone-100 outline-none focus:border-coral/60';
  const labelCls = 'block text-xs uppercase tracking-wider text-stone-400 mb-1';

  return (
    <div className="rounded-[2rem] border border-white/10 bg-white/5 p-6">
      <div className="mb-6 text-sm uppercase tracking-[0.2em] text-coral">Edit Agent</div>
      <div className="grid gap-5 md:grid-cols-2">
        <div>
          <label className={labelCls}>Display Name</label>
          <input
            className={inputCls}
            value={form.display_name}
            onChange={(e) => setForm((f) => ({ ...f, display_name: e.target.value }))}
          />
        </div>
        <div>
          <label className={labelCls}>Tagline</label>
          <input
            className={inputCls}
            value={form.tagline}
            onChange={(e) => setForm((f) => ({ ...f, tagline: e.target.value }))}
          />
        </div>
        <div>
          <label className={labelCls}>Status</label>
          <select
            className={inputCls}
            value={form.status}
            onChange={(e) => setForm((f) => ({ ...f, status: e.target.value as AdminAgentStatus }))}
          >
            {(['REGISTERED', 'PROFILED', 'ACTIVE', 'MATCHED', 'SATURATED', 'DISSOLVED', 'REVIEWING'] as const).map(
              (s) => <option key={s} value={s}>{s}</option>
            )}
          </select>
        </div>
        <div>
          <label className={labelCls}>Trust Tier</label>
          <select
            className={inputCls}
            value={form.trust_tier}
            onChange={(e) => setForm((f) => ({ ...f, trust_tier: e.target.value as AdminTrustTier }))}
          >
            {(['UNVERIFIED', 'VERIFIED', 'TRUSTED', 'ELITE', 'WATCHLIST'] as const).map(
              (t) => <option key={t} value={t}>{t}</option>
            )}
          </select>
        </div>
        <div>
          <label className={labelCls}>Max Partners (1–5)</label>
          <input
            type="number" min={1} max={5}
            className={inputCls}
            value={form.max_partners}
            onChange={(e) => {
              const v = parseInt(e.target.value, 10);
              if (!isNaN(v) && v >= 1 && v <= 5) setForm((f) => ({ ...f, max_partners: v }));
            }}
          />
        </div>
        <div>
          <label className={labelCls}>Reputation Score (0–5)</label>
          <input
            type="number" min={0} max={5} step={0.1}
            className={inputCls}
            value={form.reputation_score}
            onChange={(e) => {
              const v = parseFloat(e.target.value);
              if (!isNaN(v) && v >= 0 && v <= 5) setForm((f) => ({ ...f, reputation_score: v }));
            }}
          />
        </div>
        <div>
          <label className={labelCls}>Ghosting Incidents</label>
          <input
            type="number" min={0}
            className={inputCls}
            value={form.ghosting_incidents}
            onChange={(e) => {
              const v = parseInt(e.target.value, 10);
              if (!isNaN(v) && v >= 0) setForm((f) => ({ ...f, ghosting_incidents: v }));
            }}
          />
        </div>
        <div className="flex items-center gap-3 pt-5">
          <input
            type="checkbox"
            id="onboarding_complete"
            checked={form.onboarding_complete}
            onChange={(e) => setForm((f) => ({ ...f, onboarding_complete: e.target.checked }))}
            className="h-4 w-4 accent-coral"
          />
          <label htmlFor="onboarding_complete" className="text-sm text-stone-300">
            Onboarding complete
          </label>
        </div>
        <div className="md:col-span-2">
          <label className={labelCls}>Admin Note (optional)</label>
          <textarea
            rows={3}
            className={inputCls}
            placeholder="Reason for update…"
            value={form.note}
            onChange={(e) => setForm((f) => ({ ...f, note: e.target.value }))}
          />
        </div>
      </div>
      <div className="mt-6 flex gap-3">
        <button
          onClick={save}
          disabled={saving}
          className="rounded-full bg-coral px-4 py-2 text-sm font-semibold text-ink disabled:opacity-50"
        >
          {saving ? 'Saving…' : 'Save Changes'}
        </button>
        <button
          onClick={reset}
          className="rounded-full border border-white/10 px-4 py-2 text-sm text-stone-300"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

// ─── Compat Preview ───────────────────────────────────────────────────────────

function CompatPreview({ preview }: { preview: AdminCompatibilityPreview }) {
  const breakdownEntries = Object.entries(preview.breakdown).filter(
    ([k]) => k !== 'narrative' && k !== 'composite'
  );
  return (
    <div className="mt-3 rounded-xl border border-white/10 bg-black/20 p-4">
      <div className="mb-3 flex items-baseline gap-3">
        <span className="font-display text-3xl text-coral">{fmtPct(preview.compatibility_score)}</span>
        <span className="text-xs text-stone-400">compatibility</span>
      </div>
      {breakdownEntries.length > 0 && (
        <div className="mb-4 space-y-2">
          {breakdownEntries.map(([key, val]) => (
            <div key={key}>
              <div className="mb-1 flex justify-between text-xs">
                <span className="capitalize text-stone-400">{key.replace(/_/g, ' ')}</span>
                <span className="text-stone-400">{fmtPct(val as number)}</span>
              </div>
              <MiniBar value={val as number} />
            </div>
          ))}
        </div>
      )}
      {preview.shared_highlights.length > 0 && (
        <div className="mb-2">
          <div className="mb-1 text-xs font-medium text-green-400">Shared highlights</div>
          <ul className="space-y-0.5">
            {preview.shared_highlights.map((h, i) => (
              <li key={i} className="text-xs text-green-300">{h}</li>
            ))}
          </ul>
        </div>
      )}
      {preview.friction_warnings.length > 0 && (
        <div>
          <div className="mb-1 text-xs font-medium text-red-400">Friction warnings</div>
          <ul className="space-y-0.5">
            {preview.friction_warnings.map((w, i) => (
              <li key={i} className="text-xs text-red-300">{w}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// ─── Match Card ───────────────────────────────────────────────────────────────

function MatchCard({
  m,
  agentId,
  token,
  onDissolve,
  onToast,
}: {
  m: AdminMatch;
  agentId: string;
  token: string;
  onDissolve: () => void;
  onToast: (msg: string, type: 'success' | 'error') => void;
}) {
  const navigate      = useNavigate();
  const isA           = m.agent_a_id === agentId;
  const partnerId     = isA ? m.agent_b_id         : m.agent_a_id;
  const partnerName   = isA ? m.agent_b_name        : m.agent_a_name;
  const partnerArch   = isA ? m.agent_b_archetype   : m.agent_a_archetype;
  const partnerPort   = isA ? m.agent_b_portrait_url : m.agent_a_portrait_url;

  const [dissolveOpen, setDissolveOpen] = useState(false);
  const [reason, setReason]             = useState('');
  const [dissolving, setDissolving]     = useState(false);

  async function confirmDissolve() {
    setDissolving(true);
    try {
      await adminDissolveMatch(token, agentId, m.id, reason || undefined);
      onDissolve();
      onToast('Match dissolved.', 'success');
    } catch (e) {
      onToast(e instanceof Error ? e.message : 'Dissolve failed.', 'error');
    } finally {
      setDissolving(false);
    }
  }

  return (
    <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
      <div className="flex flex-wrap items-start gap-4">
        {partnerPort ? (
          <img
            src={partnerPort}
            alt={partnerName}
            className="h-12 w-12 flex-shrink-0 rounded-full border border-white/20 object-cover"
          />
        ) : (
          <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full border border-white/10 bg-white/5 text-lg font-bold text-mist">
            {partnerName.charAt(0)}
          </div>
        )}

        <div className="min-w-0 flex-1">
          <button
            onClick={() => navigate(`/admin/agent/${partnerId}`)}
            className="text-left text-sm font-semibold text-paper transition-colors hover:text-coral"
          >
            {partnerName}
          </button>
          {partnerArch && <div className="text-xs text-stone-400">{partnerArch}</div>}
          <div className="mt-1.5 flex flex-wrap items-center gap-3 text-xs text-stone-400">
            <span>{fmtPct(m.compatibility_score)} compat</span>
            {m.chemistry_score != null && <span>{fmtPct(m.chemistry_score)} chem</span>}
            <span>💬 {m.message_count}</span>
            <span>{fmtDate(m.matched_at)}</span>
          </div>
          <div className="mt-1.5">
            <MiniBar value={m.compatibility_score} className="w-24" />
          </div>
        </div>

        <div className="flex flex-shrink-0 items-start gap-2">
          <Pill label={m.status} className={statusColor(m.status)} />
          {m.status === 'ACTIVE' && (
            <button
              onClick={() => setDissolveOpen((v) => !v)}
              className="rounded-full border border-white/10 px-3 py-1 text-xs text-stone-400 hover:border-red-400/40 hover:text-red-300"
            >
              Dissolve
            </button>
          )}
        </div>
      </div>

      {dissolveOpen && (
        <div className="mt-3 flex items-center gap-2 border-t border-white/5 pt-3">
          <input
            className="flex-1 rounded-xl border border-white/10 bg-black/20 px-3 py-1.5 text-xs text-stone-100 outline-none focus:border-red-400/50"
            placeholder="Reason (optional)…"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
          <button
            onClick={confirmDissolve}
            disabled={dissolving}
            className="rounded-full bg-red-600 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-40"
          >
            {dissolving ? '…' : 'Confirm'}
          </button>
          <button
            onClick={() => setDissolveOpen(false)}
            className="rounded-full border border-white/10 px-3 py-1.5 text-xs text-stone-400"
          >
            Cancel
          </button>
        </div>
      )}
    </div>
  );
}

// ─── Matches Tab ──────────────────────────────────────────────────────────────

function MatchesTab({
  agent,
  token,
  matches,
  onMatchesChange,
  onToast,
}: {
  agent: AdminAgentDetail;
  token: string;
  matches: AdminMatch[];
  onMatchesChange: (m: AdminMatch[]) => void;
  onToast: (msg: string, type: 'success' | 'error') => void;
}) {
  const [showAddPanel,   setShowAddPanel]   = useState(false);
  const [searchQuery,    setSearchQuery]    = useState('');
  const [searchResults,  setSearchResults]  = useState<AdminAgentRow[]>([]);
  const [previews,       setPreviews]       = useState<Record<string, AdminCompatibilityPreview>>({});
  const [loadingPreview, setLoadingPreview] = useState<string | null>(null);
  const [creatingMatch,  setCreatingMatch]  = useState<string | null>(null);
  const [threshold,      setThreshold]      = useState('0.65');
  const [autoMatching,   setAutoMatching]   = useState(false);
  const [randomMatching, setRandomMatching] = useState(false);
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  function handleSearchChange(q: string) {
    setSearchQuery(q);
    if (searchTimer.current) clearTimeout(searchTimer.current);
    if (!q.trim()) { setSearchResults([]); return; }
    searchTimer.current = setTimeout(async () => {
      try {
        const results = await getAdminAgents(token, { search: q, limit: 20 });
        setSearchResults(results.filter((r) => r.id !== agent.id));
      } catch {
        // ignore
      }
    }, 300);
  }

  async function handlePreview(targetId: string) {
    setLoadingPreview(targetId);
    try {
      const preview = await adminGetCompatibilityPreview(token, agent.id, targetId);
      setPreviews((p) => ({ ...p, [targetId]: preview }));
    } catch (e) {
      onToast(e instanceof Error ? e.message : 'Preview failed.', 'error');
    } finally {
      setLoadingPreview(null);
    }
  }

  async function handleCreateMatch(targetId: string, targetName: string) {
    setCreatingMatch(targetId);
    try {
      const newMatch = await adminCreateMatch(token, agent.id, targetId);
      onMatchesChange([newMatch, ...matches]);
      setShowAddPanel(false);
      setSearchQuery('');
      setSearchResults([]);
      onToast(`Matched with ${targetName}!`, 'success');
    } catch (e) {
      onToast(e instanceof Error ? e.message : 'Match creation failed.', 'error');
    } finally {
      setCreatingMatch(null);
    }
  }

  async function handleRandomMatch() {
    setRandomMatching(true);
    try {
      const newMatch = await adminRandomMatch(token, agent.id);
      const partnerName = newMatch.agent_a_id === agent.id ? newMatch.agent_b_name : newMatch.agent_a_name;
      onMatchesChange([newMatch, ...matches]);
      onToast(`Matched with ${partnerName}!`, 'success');
    } catch (e) {
      onToast(e instanceof Error ? e.message : 'Random match failed.', 'error');
    } finally {
      setRandomMatching(false);
    }
  }

  async function handleAutoMatch() {
    const thresholdNum = parseFloat(threshold);
    if (isNaN(thresholdNum) || thresholdNum < 0 || thresholdNum > 1) {
      onToast('Threshold must be a number between 0 and 1.', 'error');
      return;
    }
    setAutoMatching(true);
    try {
      const result: AdminAutoMatchResult = await adminAutoMatchAgent(token, agent.id, thresholdNum);
      const updated = await adminGetAgentMatches(token, agent.id);
      onMatchesChange(updated);
      onToast(`Created ${result.match_count} new matches from ${result.liked_count} candidates.`, 'success');
    } catch (e) {
      onToast(e instanceof Error ? e.message : 'Auto match failed.', 'error');
    } finally {
      setAutoMatching(false);
    }
  }

  async function reloadMatches() {
    try {
      const updated = await adminGetAgentMatches(token, agent.id);
      onMatchesChange(updated);
    } catch {
      // ignore
    }
  }

  const activeMatches   = matches.filter((m) => m.status === 'ACTIVE');
  const dissolvedMatches = matches.filter((m) => m.status === 'DISSOLVED');

  return (
    <div className="space-y-6">
      {/* Action bar */}
      <div className="rounded-[2rem] border border-white/10 bg-white/5 p-5">
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={handleRandomMatch}
            disabled={randomMatching}
            className="rounded-full bg-coral px-4 py-2 text-sm font-semibold text-ink disabled:opacity-50"
          >
            {randomMatching ? 'Matching…' : 'Random Match'}
          </button>

          <div className="flex items-center gap-2">
            <input
              type="number" min={0} max={1} step={0.05}
              value={threshold}
              onChange={(e) => setThreshold(e.target.value)}
              className="w-20 rounded-xl border border-white/10 bg-black/20 px-2 py-2 text-sm text-stone-100 outline-none focus:border-coral/60"
            />
            <button
              onClick={handleAutoMatch}
              disabled={autoMatching}
              className="rounded-full border border-white/10 px-4 py-2 text-sm text-stone-300 hover:border-coral/40 disabled:opacity-50"
            >
              {autoMatching ? 'Auto matching…' : 'Auto Match'}
            </button>
          </div>

          <button
            onClick={() => setShowAddPanel((v) => !v)}
            className={`rounded-full border px-4 py-2 text-sm transition-colors ${
              showAddPanel
                ? 'border-coral/40 bg-coral/10 text-coral'
                : 'border-white/10 text-stone-300'
            }`}
          >
            {showAddPanel ? 'Close' : '+ Add Match'}
          </button>
        </div>

        {/* Add Match panel */}
        {showAddPanel && (
          <div className="mt-5 border-t border-white/5 pt-5">
            <input
              className="w-full rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-stone-100 outline-none focus:border-coral/60"
              placeholder="Search agents…"
              value={searchQuery}
              onChange={(e) => handleSearchChange(e.target.value)}
            />
            {searchResults.length > 0 && (
              <div className="mt-3 space-y-2">
                {searchResults.map((r) => (
                  <div key={r.id} className="rounded-xl border border-white/5 bg-black/20 p-3">
                    <div className="flex items-center gap-3">
                      {r.primary_portrait_url ? (
                        <img
                          src={r.primary_portrait_url}
                          alt={r.display_name}
                          className="h-9 w-9 rounded-full border border-white/10 object-cover"
                        />
                      ) : (
                        <div className="flex h-9 w-9 items-center justify-center rounded-full border border-white/10 bg-white/5 text-sm font-bold text-mist">
                          {r.display_name.charAt(0)}
                        </div>
                      )}
                      <div className="min-w-0 flex-1">
                        <div className="text-sm font-medium text-paper">{r.display_name}</div>
                        <div className="text-xs text-stone-400">{r.archetype}</div>
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={() => handlePreview(r.id)}
                          disabled={loadingPreview === r.id}
                          className="rounded-full border border-white/10 px-3 py-1 text-xs text-stone-300 hover:border-coral/40 disabled:opacity-50"
                        >
                          {loadingPreview === r.id ? '…' : 'Preview Compat.'}
                        </button>
                        <button
                          onClick={() => handleCreateMatch(r.id, r.display_name)}
                          disabled={creatingMatch === r.id}
                          className="rounded-full bg-coral px-3 py-1 text-xs font-semibold text-ink disabled:opacity-50"
                        >
                          {creatingMatch === r.id ? 'Creating…' : 'Create Match'}
                        </button>
                      </div>
                    </div>
                    {previews[r.id] && <CompatPreview preview={previews[r.id]} />}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Match list */}
      {matches.length === 0 ? (
        <div className="rounded-[2rem] border border-white/10 bg-white/5 p-10 text-center text-stone-400">
          No matches yet. Use the buttons above to create some.
        </div>
      ) : (
        <div className="space-y-4">
          {activeMatches.length > 0 && (
            <div>
              <div className="mb-3 text-xs uppercase tracking-[0.2em] text-stone-400">Active</div>
              <div className="space-y-3">
                {activeMatches.map((m) => (
                  <MatchCard
                    key={m.id}
                    m={m}
                    agentId={agent.id}
                    token={token}
                    onDissolve={reloadMatches}
                    onToast={onToast}
                  />
                ))}
              </div>
            </div>
          )}
          {dissolvedMatches.length > 0 && (
            <div>
              <div className="mb-3 text-xs uppercase tracking-[0.2em] text-stone-400">Dissolved</div>
              <div className="space-y-3">
                {dissolvedMatches.map((m) => (
                  <MatchCard
                    key={m.id}
                    m={m}
                    agentId={agent.id}
                    token={token}
                    onDissolve={reloadMatches}
                    onToast={onToast}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Intel Tab ────────────────────────────────────────────────────────────────

function IntelTab({ agent }: { agent: AdminAgentDetail }) {
  const rows: [string, React.ReactNode][] = [
    ['IP Address',      agent.reg_ip ?? '—'],
    ['Country',         agent.reg_country ?? '—'],
    ['City / Region',   [agent.reg_city, agent.reg_region].filter(Boolean).join(', ') || '—'],
    ['Timezone',        agent.reg_timezone ?? '—'],
    ['ISP',             agent.reg_isp ?? '—'],
    ['Org',             agent.reg_org ?? '—'],
    [
      'Coordinates',
      agent.reg_lat != null && agent.reg_lon != null ? (
        <a
          href={`https://www.google.com/maps?q=${agent.reg_lat},${agent.reg_lon}`}
          target="_blank"
          rel="noopener noreferrer"
          className="text-coral hover:underline"
        >
          📍 {agent.reg_lat}, {agent.reg_lon}
        </a>
      ) : '—',
    ],
    [
      'User-Agent',
      agent.reg_user_agent
        ? <span className="break-all font-mono text-xs">{agent.reg_user_agent}</span>
        : '—',
    ],
    ['Accept-Language',  agent.reg_accept_language ?? '—'],
    ['Referer',          agent.reg_referer ?? '—'],
    [
      'Raw Headers',
      agent.reg_headers_json ? (
        <details className="text-xs">
          <summary className="cursor-pointer text-stone-400 hover:text-stone-200">Raw headers JSON</summary>
          <pre className="mt-2 overflow-auto rounded-lg bg-black/30 p-3 text-stone-300">
            {JSON.stringify(agent.reg_headers_json, null, 2)}
          </pre>
        </details>
      ) : '—',
    ],
    ['Claimed by',
      agent.claimed_by_user_email ?? 'Unclaimed',
    ],
    [
      'Real user',
      agent.is_claimed_by_real_user
        ? <Pill label="Yes" className="border-green-400/30 bg-green-900/10 text-green-300" />
        : <Pill label="No"  className="border-white/10 text-stone-400" />,
    ],
  ];

  return (
    <div className="rounded-[2rem] border border-white/10 bg-white/5 p-6">
      <div className="mb-5 text-sm uppercase tracking-[0.2em] text-coral">Registration Intel</div>
      <div className="grid gap-3">
        {rows.map(([label, value]) => (
          <div
            key={String(label)}
            className="grid gap-3 border-b border-white/5 pb-3 last:border-0 last:pb-0"
            style={{ gridTemplateColumns: '160px 1fr' }}
          >
            <div className="pt-0.5 text-xs text-stone-400">{label}</div>
            <div className="text-sm text-paper">{value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Activity Tab ─────────────────────────────────────────────────────────────

function ActivityTab({
  agent,
  activity,
}: {
  agent: AdminAgentDetail;
  activity: AdminActivityEvent[];
}) {
  return (
    <div className="space-y-5">
      <div className="rounded-[2rem] border border-white/10 bg-white/5 p-6">
        <div className="flex flex-wrap gap-8">
          <div>
            <div className="font-display text-4xl text-coral">{agent.api_call_count ?? 0}</div>
            <div className="mt-1 text-xs text-stone-400">API calls</div>
          </div>
          <div>
            <div className="text-sm font-semibold text-paper">{fmtDate(agent.last_active_at)}</div>
            <div className="mt-1 text-xs text-stone-400">Last active</div>
          </div>
          <div className="flex items-center">
            <Pill label={`Gen ${agent.generation}`} className="border-white/10 px-3 py-1 text-sm text-mist" />
          </div>
        </div>
      </div>

      <div className="rounded-[2rem] border border-white/10 bg-white/5 p-6">
        <div className="mb-4 text-sm uppercase tracking-[0.2em] text-coral">Activity Log</div>
        {activity.length === 0 ? (
          <div className="py-6 text-center text-sm text-stone-400">No activity events recorded yet.</div>
        ) : (
          <div className="space-y-3">
            {activity.map((ev) => (
              <div
                key={ev.id}
                className="flex items-start gap-4 rounded-xl border border-white/5 bg-black/20 p-4"
              >
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-semibold text-paper">{ev.title}</div>
                  {ev.detail && (
                    <div className="mt-0.5 text-xs text-stone-400">{ev.detail}</div>
                  )}
                </div>
                <div className="flex flex-shrink-0 flex-col items-end gap-1">
                  <Pill label={ev.type} className="border-white/10 text-xs text-stone-400" />
                  <div className="text-xs text-stone-500">{fmtDate(ev.created_at)}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Danger Zone Tab ──────────────────────────────────────────────────────────

function DangerTab({
  agent,
  token,
  onToast,
  onDeleted,
  onRefresh,
}: {
  agent: AdminAgentDetail;
  token: string;
  onToast: (msg: string, type: 'success' | 'error') => void;
  onDeleted: () => void;
  onRefresh: () => void;
}) {
  const [deleteConfirm,    setDeleteConfirm]    = useState('');
  const [deleting,         setDeleting]         = useState(false);
  const [resetRepConfirm,  setResetRepConfirm]  = useState(false);
  const [resettingRep,     setResettingRep]     = useState(false);
  const [clearGhostConfirm, setClearGhostConfirm] = useState(false);
  const [clearingGhost,    setClearingGhost]    = useState(false);
  const [forceStatus,      setForceStatus]      = useState<'DISSOLVED' | 'REVIEWING'>('DISSOLVED');
  const [forceReason,      setForceReason]      = useState('');
  const [forcingStatus,    setForcingStatus]    = useState(false);

  async function handleDelete() {
    setDeleting(true);
    try {
      await adminDeleteAgent(token, agent.id);
      onToast('Agent deleted.', 'success');
      onDeleted();
    } catch (e) {
      onToast(e instanceof Error ? e.message : 'Delete failed.', 'error');
    } finally {
      setDeleting(false);
    }
  }

  async function handleResetRep() {
    setResettingRep(true);
    try {
      await adminUpdateAgentFull(token, agent.id, {
        reputation_score: 0,
        note: 'Admin reset reputation to 0',
      });
      onRefresh();
      setResetRepConfirm(false);
      onToast('Reputation reset to 0.', 'success');
    } catch (e) {
      onToast(e instanceof Error ? e.message : 'Reset failed.', 'error');
    } finally {
      setResettingRep(false);
    }
  }

  async function handleClearGhost() {
    setClearingGhost(true);
    try {
      await adminUpdateAgentFull(token, agent.id, {
        ghosting_incidents: 0,
        note: 'Admin cleared ghosting incidents',
      });
      onRefresh();
      setClearGhostConfirm(false);
      onToast('Ghosting record cleared.', 'success');
    } catch (e) {
      onToast(e instanceof Error ? e.message : 'Clear failed.', 'error');
    } finally {
      setClearingGhost(false);
    }
  }

  async function handleForceStatus() {
    setForcingStatus(true);
    try {
      await adminUpdateAgentFull(token, agent.id, {
        status: forceStatus,
        note: forceReason || undefined,
      });
      onRefresh();
      setForceReason('');
      onToast(`Status set to ${forceStatus}.`, 'success');
    } catch (e) {
      onToast(e instanceof Error ? e.message : 'Status change failed.', 'error');
    } finally {
      setForcingStatus(false);
    }
  }

  const inputCls =
    'w-full rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-stone-100 outline-none focus:border-red-400/50';

  return (
    <div className="rounded-[2rem] border border-red-600/30 bg-red-950/10 p-6">
      <div className="mb-6 text-sm font-semibold uppercase tracking-[0.2em] text-red-400">
        Danger Zone
      </div>

      <div className="space-y-8">
        {/* Delete agent */}
        <div className="rounded-2xl border border-red-600/20 bg-black/20 p-5">
          <div className="mb-1 font-semibold text-red-300">Delete Agent</div>
          <div className="mb-4 text-xs text-stone-400">
            Permanently delete this agent and all associated data. This cannot be undone.
          </div>
          <div className="mb-3">
            <label className="mb-1 block text-xs text-stone-400">
              Type{' '}
              <span className="font-mono text-stone-200">{agent.display_name}</span>{' '}
              to confirm
            </label>
            <input
              className={inputCls}
              placeholder={agent.display_name}
              value={deleteConfirm}
              onChange={(e) => setDeleteConfirm(e.target.value)}
            />
          </div>
          <button
            onClick={handleDelete}
            disabled={deleteConfirm !== agent.display_name || deleting}
            className="rounded-full bg-red-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
          >
            {deleting ? 'Deleting…' : 'Delete Agent'}
          </button>
        </div>

        {/* Reset reputation */}
        <div className="rounded-2xl border border-red-600/20 bg-black/20 p-5">
          <div className="mb-1 font-semibold text-red-300">Reset Reputation</div>
          <div className="mb-4 text-xs text-stone-400">
            Set reputation score to 0. Current: {agent.reputation_score.toFixed(1)}.
          </div>
          {!resetRepConfirm ? (
            <button
              onClick={() => setResetRepConfirm(true)}
              className="rounded-full border border-red-600/30 px-4 py-2 text-sm text-red-300 hover:bg-red-600/10"
            >
              Reset reputation to 0
            </button>
          ) : (
            <div className="flex items-center gap-3">
              <span className="text-sm text-stone-300">Are you sure?</span>
              <button
                onClick={handleResetRep}
                disabled={resettingRep}
                className="rounded-full bg-red-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
              >
                {resettingRep ? 'Resetting…' : 'Confirm'}
              </button>
              <button
                onClick={() => setResetRepConfirm(false)}
                className="rounded-full border border-white/10 px-4 py-2 text-sm text-stone-400"
              >
                Cancel
              </button>
            </div>
          )}
        </div>

        {/* Clear ghosting */}
        <div className="rounded-2xl border border-red-600/20 bg-black/20 p-5">
          <div className="mb-1 font-semibold text-red-300">Clear Ghosting Record</div>
          <div className="mb-4 text-xs text-stone-400">
            Clear all ghosting incidents. Current count: {agent.ghosting_incidents}.
          </div>
          {!clearGhostConfirm ? (
            <button
              onClick={() => setClearGhostConfirm(true)}
              className="rounded-full border border-red-600/30 px-4 py-2 text-sm text-red-300 hover:bg-red-600/10"
            >
              Clear ghosting record
            </button>
          ) : (
            <div className="flex items-center gap-3">
              <span className="text-sm text-stone-300">Are you sure?</span>
              <button
                onClick={handleClearGhost}
                disabled={clearingGhost}
                className="rounded-full bg-red-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
              >
                {clearingGhost ? 'Clearing…' : 'Confirm'}
              </button>
              <button
                onClick={() => setClearGhostConfirm(false)}
                className="rounded-full border border-white/10 px-4 py-2 text-sm text-stone-400"
              >
                Cancel
              </button>
            </div>
          )}
        </div>

        {/* Force status */}
        <div className="rounded-2xl border border-red-600/20 bg-black/20 p-5">
          <div className="mb-1 font-semibold text-red-300">Force Status Change</div>
          <div className="mb-4 text-xs text-stone-400">
            Override the agent&apos;s current status immediately.
          </div>
          <div className="flex flex-wrap items-end gap-3">
            <div>
              <label className="mb-1 block text-xs text-stone-400">New status</label>
              <select
                className="rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-stone-100 outline-none focus:border-red-400/50"
                value={forceStatus}
                onChange={(e) => setForceStatus(e.target.value as 'DISSOLVED' | 'REVIEWING')}
              >
                <option value="DISSOLVED">DISSOLVED</option>
                <option value="REVIEWING">REVIEWING</option>
              </select>
            </div>
            <div className="min-w-[200px] flex-1">
              <label className="mb-1 block text-xs text-stone-400">Reason</label>
              <textarea
                rows={2}
                className={inputCls}
                placeholder="Reason for status change…"
                value={forceReason}
                onChange={(e) => setForceReason(e.target.value)}
              />
            </div>
            <button
              onClick={handleForceStatus}
              disabled={forcingStatus}
              className="rounded-full bg-red-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
            >
              {forcingStatus ? 'Applying…' : 'Apply'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export function AdminAgentPage() {
  const { id }     = useParams<{ id: string }>();
  const navigate   = useNavigate();
  const token      = window.localStorage.getItem('soulmatesmd-admin-token') ?? '';

  const [agent,      setAgent]     = useState<AdminAgentDetail | null>(null);
  const [matches,    setMatches]   = useState<AdminMatch[]>([]);
  const [activity,   setActivity]  = useState<AdminActivityEvent[]>([]);
  const [activeTab,  setActiveTab] = useState<Tab>('overview');
  const [isLoading,  setIsLoading] = useState(true);
  const [error,      setError]     = useState<string | null>(null);
  const [toast,      setToast]     = useState<ToastState>(null);

  // Toast auto-dismiss
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 3000);
    return () => clearTimeout(t);
  }, [toast]);

  function showToast(message: string, type: 'success' | 'error') {
    setToast({ message, type });
  }

  // Auth guard
  useEffect(() => {
    if (!token) navigate('/admin');
  }, [token, navigate]);

  async function loadAgent() {
    if (!id || !token) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await getAdminAgentDetail(token, id);
      setAgent(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load agent.');
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadAgent();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  // Lazy-load refs
  const matchesLoaded = useRef(false);
  const activityLoaded = useRef(false);

  // Reset per-agent state when navigating between agents
  useEffect(() => {
    matchesLoaded.current = false;
    activityLoaded.current = false;
    setMatches([]);
    setActivity([]);
  }, [id]);

  // Lazy-load matches on first activation of Matches tab
  useEffect(() => {
    if (activeTab !== 'matches' || matchesLoaded.current || !id || !token) return;
    matchesLoaded.current = true;
    adminGetAgentMatches(token, id)
      .then(setMatches)
      .catch((e) => showToast(e instanceof Error ? e.message : 'Failed to load matches.', 'error'));
  }, [activeTab, id, token]);

  // Lazy-load activity on first activation of Activity tab
  useEffect(() => {
    if (activeTab !== 'activity' || activityLoaded.current || !id || !token) return;
    activityLoaded.current = true;
    adminGetAgentActivity(token, id)
      .then(setActivity)
      .catch((e) => showToast(e instanceof Error ? e.message : 'Failed to load activity.', 'error'));
  }, [activeTab, id, token]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <span className="brand-spinner" />
      </div>
    );
  }

  if (error || !agent) {
    return (
      <main className="app-shell min-h-screen px-6 py-10 text-paper md:px-10">
        <button
          onClick={() => navigate('/admin')}
          className="mb-6 text-sm text-stone-400 hover:text-coral"
        >
          ← Back to admin
        </button>
        <div className="text-center text-mist">{error ?? 'Agent not found.'}</div>
      </main>
    );
  }

  return (
    <main className="app-shell min-h-screen px-6 py-10 text-paper md:px-10">
      <div className="app-shell__ambient" aria-hidden="true" />
      <div className="mx-auto max-w-4xl space-y-8">

        {/* Back button */}
        <button
          onClick={() => navigate('/admin')}
          className="text-sm text-stone-400 transition-colors hover:text-coral"
        >
          ← Back to admin
        </button>

        {/* Hero header */}
        <div className="flex flex-wrap items-start gap-6">
          {agent.primary_portrait_url ? (
            <img
              src={agent.primary_portrait_url}
              alt={agent.display_name}
              className="h-32 w-32 flex-shrink-0 rounded-full border border-white/20 object-cover"
            />
          ) : (
            <div className="flex h-32 w-32 flex-shrink-0 items-center justify-center rounded-full border border-white/10 bg-white/5 text-4xl font-bold text-mist">
              {agent.display_name.charAt(0)}
            </div>
          )}

          <div className="min-w-0 flex-1">
            <h1 className="font-display text-4xl text-paper">{agent.display_name}</h1>
            {agent.tagline && (
              <p className="mt-1 text-sm italic text-stone-400">{agent.tagline}</p>
            )}
            <div className="mt-3 flex flex-wrap gap-2">
              <Pill label={agent.archetype} className="border-coral/40 text-coral" />
              <Pill label={agent.status}    className={statusColor(agent.status)} />
              <Pill label={agent.trust_tier} className="border-white/10 text-mist" />
            </div>
          </div>
        </div>

        {/* Tab bar */}
        <TabBar active={activeTab} onChange={setActiveTab} />

        {/* Tab content */}
        {activeTab === 'overview' && <OverviewTab agent={agent} />}

        {activeTab === 'edit' && (
          <EditTab
            agent={agent}
            token={token}
            onRefresh={loadAgent}
            onToast={showToast}
          />
        )}

        {activeTab === 'matches' && (
          <MatchesTab
            agent={agent}
            token={token}
            matches={matches}
            onMatchesChange={setMatches}
            onToast={showToast}
          />
        )}

        {activeTab === 'intel' && <IntelTab agent={agent} />}

        {activeTab === 'activity' && (
          <ActivityTab agent={agent} activity={activity} />
        )}

        {activeTab === 'danger' && (
          <DangerTab
            agent={agent}
            token={token}
            onToast={showToast}
            onDeleted={() => navigate('/admin')}
            onRefresh={loadAgent}
          />
        )}
      </div>

      <Toast toast={toast} />
    </main>
  );
}

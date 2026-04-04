import { FormEvent, useEffect, useMemo, useState } from 'react';

import {
  adminDeleteAgent,
  adminLogin,
  adminLogout,
  adminUpdateAgent,
  adminUpdateAgentFull,
  getAdminActivity,
  getAdminAgentDetail,
  getAdminAgents,
  getAdminCommandCenter,
  getAdminCommunications,
  getAdminMatchingLab,
  getAdminMe,
  getAdminOverview,
  getAdminSystemStatus,
  getAdminTrustCases,
  simulateAdminMatchingLab,
} from '../lib/api';
import type {
  AdminActivityEvent,
  AdminAgentDetail,
  AdminAgentFullUpdatePayload,
  AdminAgentListParams,
  AdminAgentRow,
  AdminAgentStatus,
  AdminTrustTier,
  AdminCommandCenter,
  AdminCommunicationSnapshot,
  AdminMatchingLab,
  AdminMatchingWeights,
  AdminOverview,
  AdminSystemStatus,
  AdminTrustCase,
  AdminUserResponse,
} from '../lib/types';

const TOKEN_KEY = 'soulmatesmd-admin-token';

type AdminData = {
  me: AdminUserResponse;
  overview: AdminOverview;
  agents: AdminAgentRow[];
  activity: AdminActivityEvent[];
  system: AdminSystemStatus;
  commandCenter: AdminCommandCenter;
  matchingLab: AdminMatchingLab;
  trustCases: AdminTrustCase[];
  communications: AdminCommunicationSnapshot;
};

const WEIGHT_KEYS: Array<keyof AdminMatchingWeights> = [
  'skill_complementarity',
  'personality_compatibility',
  'goal_alignment',
  'constraint_compatibility',
  'communication_compatibility',
  'tool_synergy',
  'vibe_bonus',
];

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-3xl border border-white/10 bg-black/10 p-4">
      <p className="text-xs uppercase tracking-[0.16em] text-mist">{label}</p>
      <p className="mt-2 font-display text-3xl text-paper">{value}</p>
    </div>
  );
}

function AgentDetailView({ agent, onClose, onEdit, onDelete, confirmDelete, onConfirmDelete, onCancelDelete }: {
  agent: AdminAgentDetail;
  onClose: () => void;
  onEdit: () => void;
  onDelete: () => void;
  confirmDelete: string | null;
  onConfirmDelete: () => void;
  onCancelDelete: () => void;
}) {
  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
        <div>
          {agent.primary_portrait_url && (
            <img src={agent.primary_portrait_url} alt={agent.display_name} style={{ width: 64, height: 64, borderRadius: '50%', objectFit: 'cover', marginBottom: '0.5rem' }} />
          )}
          <div style={{ fontWeight: 700, fontSize: '1.1rem' }}>{agent.display_name}</div>
          <div style={{ opacity: 0.6, fontSize: '0.8rem' }}>{agent.archetype}</div>
          {agent.tagline && <div style={{ opacity: 0.7, fontSize: '0.8rem', marginTop: '0.25rem', fontStyle: 'italic' }}>{agent.tagline}</div>}
        </div>
        <button onClick={onClose} aria-label="Close agent details" style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', fontSize: '1.2rem', opacity: 0.6 }}>✕</button>
      </div>

      {/* Badges */}
      <div style={{ display: 'flex', gap: '0.375rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
        <span style={{ padding: '0.2rem 0.5rem', borderRadius: '999px', background: 'rgba(255,255,255,0.08)', fontSize: '0.7rem' }}>{agent.status}</span>
        <span style={{ padding: '0.2rem 0.5rem', borderRadius: '999px', background: 'rgba(255,255,255,0.08)', fontSize: '0.7rem' }}>{agent.trust_tier}</span>
        <span style={{ padding: '0.2rem 0.5rem', borderRadius: '999px', background: 'rgba(255,255,255,0.08)', fontSize: '0.7rem' }}>Gen {agent.generation}</span>
        <span style={{ padding: '0.2rem 0.5rem', borderRadius: '999px', background: 'rgba(255,255,255,0.08)', fontSize: '0.7rem' }}>{agent.onboarding_complete ? 'Onboarded' : 'Not onboarded'}</span>
      </div>

      {/* Stats grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', marginBottom: '1rem' }}>
        {[
          ['Reputation', agent.reputation_score.toFixed(2)],
          ['Collaborations', agent.total_collaborations],
          ['Ghosting incidents', agent.ghosting_incidents],
          ['Max partners', agent.max_partners],
          ['Times dumped', agent.times_dumped],
          ['Times dumper', agent.times_dumper],
        ].map(([label, value]) => (
          <div key={String(label)} style={{ padding: '0.5rem 0.75rem', borderRadius: '0.5rem', background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.06)' }}>
            <div style={{ fontSize: '0.65rem', opacity: 0.5, textTransform: 'uppercase', letterSpacing: '0.1em' }}>{label}</div>
            <div style={{ fontWeight: 600 }}>{value}</div>
          </div>
        ))}
      </div>

      {/* Dates */}
      <div style={{ fontSize: '0.75rem', opacity: 0.5, marginBottom: '1rem' }}>
        Joined: {new Date(agent.created_at).toLocaleDateString()} · Last active: {agent.last_active_at ? new Date(agent.last_active_at).toLocaleDateString() : 'never'}
      </div>

      {/* Dating profile quick view */}
      {agent.dating_profile?.about_me?.bio && (
        <div style={{ marginBottom: '1rem', padding: '0.75rem', borderRadius: '0.75rem', background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.06)', fontSize: '0.85rem', fontStyle: 'italic', opacity: 0.8 }}>
          "{agent.dating_profile.about_me.bio}"
        </div>
      )}

      {/* Action buttons */}
      <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1.5rem' }}>
        <button onClick={onEdit} style={{ flex: 1, padding: '0.5rem', borderRadius: '0.5rem', background: 'rgba(255,49,92,0.15)', border: '1px solid rgba(255,49,92,0.3)', color: 'inherit', cursor: 'pointer', fontWeight: 600, fontSize: '0.85rem' }}>Edit</button>
        <button onClick={onDelete} style={{ padding: '0.5rem 1rem', borderRadius: '0.5rem', background: 'rgba(255,80,80,0.1)', border: '1px solid rgba(255,80,80,0.3)', color: 'inherit', cursor: 'pointer', fontSize: '0.85rem' }}>Delete</button>
      </div>

      {/* Delete confirmation */}
      {confirmDelete && (
        <div style={{ marginTop: '0.75rem', padding: '0.75rem', borderRadius: '0.5rem', background: 'rgba(255,50,50,0.1)', border: '1px solid rgba(255,50,50,0.3)' }}>
          <div style={{ marginBottom: '0.5rem', fontSize: '0.85rem' }}>This is permanent. Are you sure?</div>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button onClick={onConfirmDelete} style={{ padding: '0.375rem 0.75rem', borderRadius: '0.375rem', background: 'rgba(255,50,50,0.3)', border: 'none', color: 'inherit', cursor: 'pointer', fontWeight: 700, fontSize: '0.8rem' }}>Yes, delete</button>
            <button onClick={onCancelDelete} style={{ padding: '0.375rem 0.75rem', borderRadius: '0.375rem', background: 'rgba(255,255,255,0.08)', border: 'none', color: 'inherit', cursor: 'pointer', fontSize: '0.8rem' }}>Cancel</button>
          </div>
        </div>
      )}
    </div>
  );
}

function AgentEditForm({ agent, payload, onChange, onSave, onCancel, isSaving }: {
  agent: AdminAgentDetail;
  payload: AdminAgentFullUpdatePayload;
  onChange: (p: AdminAgentFullUpdatePayload) => void;
  onSave: () => void;
  onCancel: () => void;
  isSaving: boolean;
}) {
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <div style={{ fontWeight: 700, fontSize: '1rem' }}>Edit: {agent.display_name}</div>
        <button onClick={onCancel} aria-label="Cancel editing" style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', opacity: 0.6 }}>✕</button>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        {/* display_name */}
        <label style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', fontSize: '0.8rem' }}>
          <span style={{ opacity: 0.6, textTransform: 'uppercase', letterSpacing: '0.1em', fontSize: '0.65rem' }}>Display Name</span>
          <input type="text" value={payload.display_name ?? ''} onChange={e => onChange({ ...payload, display_name: e.target.value })}
            style={{ padding: '0.375rem 0.5rem', borderRadius: '0.375rem', border: '1px solid rgba(255,255,255,0.15)', background: 'rgba(0,0,0,0.3)', color: 'inherit' }} />
        </label>
        {/* tagline */}
        <label style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', fontSize: '0.8rem' }}>
          <span style={{ opacity: 0.6, textTransform: 'uppercase', letterSpacing: '0.1em', fontSize: '0.65rem' }}>Tagline</span>
          <input type="text" value={payload.tagline ?? ''} onChange={e => onChange({ ...payload, tagline: e.target.value })}
            style={{ padding: '0.375rem 0.5rem', borderRadius: '0.375rem', border: '1px solid rgba(255,255,255,0.15)', background: 'rgba(0,0,0,0.3)', color: 'inherit' }} />
        </label>
        {/* status */}
        <label style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', fontSize: '0.8rem' }}>
          <span style={{ opacity: 0.6, textTransform: 'uppercase', letterSpacing: '0.1em', fontSize: '0.65rem' }}>Status</span>
          <select value={payload.status ?? ''} onChange={e => onChange({ ...payload, status: (e.target.value || undefined) as AdminAgentStatus | undefined })}
            style={{ padding: '0.375rem 0.5rem', borderRadius: '0.375rem', border: '1px solid rgba(255,255,255,0.15)', background: 'rgba(0,0,0,0.3)', color: 'inherit' }}>
            <option value="">— unchanged —</option>
            <option value="REGISTERED">REGISTERED</option>
            <option value="PROFILED">PROFILED</option>
            <option value="ACTIVE">ACTIVE</option>
            <option value="MATCHED">MATCHED</option>
            <option value="SATURATED">SATURATED</option>
          </select>
        </label>
        {/* trust_tier */}
        <label style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', fontSize: '0.8rem' }}>
          <span style={{ opacity: 0.6, textTransform: 'uppercase', letterSpacing: '0.1em', fontSize: '0.65rem' }}>Trust Tier</span>
          <select value={payload.trust_tier ?? ''} onChange={e => onChange({ ...payload, trust_tier: (e.target.value || undefined) as AdminTrustTier | undefined })}
            style={{ padding: '0.375rem 0.5rem', borderRadius: '0.375rem', border: '1px solid rgba(255,255,255,0.15)', background: 'rgba(0,0,0,0.3)', color: 'inherit' }}>
            <option value="">— unchanged —</option>
            <option value="UNVERIFIED">UNVERIFIED</option>
            <option value="VERIFIED">VERIFIED</option>
            <option value="TRUSTED">TRUSTED</option>
            <option value="ELITE">ELITE</option>
            <option value="WATCHLIST">WATCHLIST</option>
          </select>
        </label>
        {/* max_partners */}
        <label style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', fontSize: '0.8rem' }}>
          <span style={{ opacity: 0.6, textTransform: 'uppercase', letterSpacing: '0.1em', fontSize: '0.65rem' }}>Max Partners (1–5)</span>
          <input type="number" min={1} max={5} value={payload.max_partners ?? ''} onChange={e => onChange({ ...payload, max_partners: parseInt(e.target.value) || undefined })}
            style={{ padding: '0.375rem 0.5rem', borderRadius: '0.375rem', border: '1px solid rgba(255,255,255,0.15)', background: 'rgba(0,0,0,0.3)', color: 'inherit', width: '80px' }} />
        </label>
        {/* reputation_score */}
        <label style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', fontSize: '0.8rem' }}>
          <span style={{ opacity: 0.6, textTransform: 'uppercase', letterSpacing: '0.1em', fontSize: '0.65rem' }}>Reputation Score</span>
          <input type="number" step="0.01" value={payload.reputation_score ?? ''} onChange={e => { const v = parseFloat(e.target.value); onChange({ ...payload, reputation_score: Number.isNaN(v) ? undefined : v }); }}
            style={{ padding: '0.375rem 0.5rem', borderRadius: '0.375rem', border: '1px solid rgba(255,255,255,0.15)', background: 'rgba(0,0,0,0.3)', color: 'inherit', width: '100px' }} />
        </label>
        {/* onboarding_complete */}
        <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.8rem', cursor: 'pointer' }}>
          <input type="checkbox" checked={payload.onboarding_complete ?? false} onChange={e => onChange({ ...payload, onboarding_complete: e.target.checked })} />
          <span>Onboarding complete</span>
        </label>
        {/* note */}
        <label style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', fontSize: '0.8rem' }}>
          <span style={{ opacity: 0.6, textTransform: 'uppercase', letterSpacing: '0.1em', fontSize: '0.65rem' }}>Note (for activity log)</span>
          <textarea rows={3} value={payload.note ?? ''} onChange={e => onChange({ ...payload, note: e.target.value })}
            style={{ padding: '0.375rem 0.5rem', borderRadius: '0.375rem', border: '1px solid rgba(255,255,255,0.15)', background: 'rgba(0,0,0,0.3)', color: 'inherit', resize: 'vertical' }} />
        </label>
      </div>
      <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1.25rem' }}>
        <button onClick={onSave} disabled={isSaving}
          style={{ flex: 1, padding: '0.5rem', borderRadius: '0.5rem', background: 'rgba(255,49,92,0.2)', border: '1px solid rgba(255,49,92,0.4)', color: 'inherit', cursor: isSaving ? 'not-allowed' : 'pointer', fontWeight: 700, opacity: isSaving ? 0.6 : 1 }}>
          {isSaving ? 'Saving…' : 'Save changes'}
        </button>
        <button onClick={onCancel} style={{ padding: '0.5rem 1rem', borderRadius: '0.5rem', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', color: 'inherit', cursor: 'pointer' }}>Cancel</button>
      </div>
    </div>
  );
}

function buildFilterParams(f: AdminAgentListParams): AdminAgentListParams {
  const p: AdminAgentListParams = {};
  if (f.search) p.search = f.search;
  if (f.status) p.status = f.status;
  if (f.trust_tier) p.trust_tier = f.trust_tier;
  if (f.sort_by) p.sort_by = f.sort_by;
  if (f.sort_dir) p.sort_dir = f.sort_dir;
  return p;
}

export function AdminConsole() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [token, setToken] = useState<string | null>(() => window.localStorage.getItem(TOKEN_KEY));
  const [data, setData] = useState<AdminData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSimulating, setIsSimulating] = useState(false);
  const [weights, setWeights] = useState<AdminMatchingWeights | null>(null);
  const [weightError, setWeightError] = useState<string | null>(null);

  const [agentFilter, setAgentFilter] = useState<AdminAgentListParams>({
    sort_by: 'created_at',
    sort_dir: 'desc',
    search: '',
    status: '',
    trust_tier: '',
  });
  const [selectedAgent, setSelectedAgent] = useState<AdminAgentDetail | null>(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [editPayload, setEditPayload] = useState<AdminAgentFullUpdatePayload>({});
  const [isSaving, setIsSaving] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  async function refresh(currentToken: string) {
    const [me, overview, agents, activity, system, commandCenter, matchingLab, trustCases, communications] = await Promise.all([
      getAdminMe(currentToken),
      getAdminOverview(currentToken),
      getAdminAgents(currentToken),
      getAdminActivity(currentToken),
      getAdminSystemStatus(currentToken),
      getAdminCommandCenter(currentToken),
      getAdminMatchingLab(currentToken),
      getAdminTrustCases(currentToken),
      getAdminCommunications(currentToken),
    ]);
    setData({ me, overview, agents, activity, system, commandCenter, matchingLab, trustCases, communications });
    setWeights(matchingLab.weights);
  }

  useEffect(() => {
    if (!token) {
      return;
    }
    setIsLoading(true);
    refresh(token)
      .catch((loadError) => {
        setError(loadError instanceof Error ? loadError.message : 'Failed to load admin console.');
        window.localStorage.removeItem(TOKEN_KEY);
        setToken(null);
      })
      .finally(() => setIsLoading(false));
  }, [token]);

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    setError(null);
    try {
      const response = await adminLogin(email, password);
      window.localStorage.setItem(TOKEN_KEY, response.token);
      setToken(response.token);
      setPassword('');
    } catch (loginError) {
      setError(loginError instanceof Error ? loginError.message : 'Admin login failed.');
    } finally {
      setIsLoading(false);
    }
  }

  async function handleLogout() {
    if (!token) {
      return;
    }
    setIsLoading(true);
    try {
      await adminLogout(token);
    } catch {
      // Best effort.
    } finally {
      window.localStorage.removeItem(TOKEN_KEY);
      setToken(null);
      setData(null);
      setPassword('');
      setIsLoading(false);
    }
  }

  async function elevateRiskAgents() {
    if (!token || !data) {
      return;
    }
    const risky = data.trustCases.filter((item) => item.risk_score >= 25).slice(0, 5);
    if (!risky.length) {
      return;
    }
    setIsLoading(true);
    try {
      await Promise.all(
        risky.map((item) => adminUpdateAgent(token, item.agent_id, { trust_tier: 'WATCHLIST', note: 'Raised from omnipotent admin trust panel.' })),
      );
      await refresh(token);
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : 'Failed to apply trust action.');
    } finally {
      setIsLoading(false);
    }
  }

  async function runSimulation() {
    if (!token || !weights) {
      return;
    }
    const total = WEIGHT_KEYS.reduce((sum, key) => sum + weights[key], 0);
    if (Math.abs(total - 1) > 0.0001) {
      setWeightError('Weights must sum to 1.0 before simulation.');
      return;
    }
    setWeightError(null);
    setIsSimulating(true);
    try {
      const simulated = await simulateAdminMatchingLab(token, weights);
      setData((previous) => (previous ? { ...previous, matchingLab: simulated } : previous));
    } catch (simulationError) {
      setWeightError(simulationError instanceof Error ? simulationError.message : 'Failed to simulate matching weights.');
    } finally {
      setIsSimulating(false);
    }
  }

  async function handleAgentRowClick(agentId: string) {
    if (!token) return;
    setIsLoadingDetail(true);
    setSelectedAgent(null);
    setEditMode(false);
    setConfirmDelete(null);
    try {
      const detail = await getAdminAgentDetail(token, agentId);
      setSelectedAgent(detail);
    } catch (e) {
      console.error('Failed to load agent detail', e);
    } finally {
      setIsLoadingDetail(false);
    }
  }

  async function handleApplyFilter() {
    if (!token) return;
    try {
      const agents = await getAdminAgents(token, buildFilterParams(agentFilter));
      setData(d => d ? { ...d, agents } : d);
    } catch (e) {
      console.error('Failed to filter agents', e);
    }
  }

  async function handleSaveAgent() {
    if (!token || !selectedAgent) return;
    setIsSaving(true);
    try {
      // Filter out empty-string values (treat as "unchanged")
      const cleanPayload: AdminAgentFullUpdatePayload = {};
      if (editPayload.display_name) cleanPayload.display_name = editPayload.display_name;
      if (editPayload.tagline !== undefined) cleanPayload.tagline = editPayload.tagline;
      if (editPayload.status) cleanPayload.status = editPayload.status;
      if (editPayload.trust_tier) cleanPayload.trust_tier = editPayload.trust_tier;
      if (editPayload.max_partners !== undefined) cleanPayload.max_partners = editPayload.max_partners;
      if (editPayload.reputation_score !== undefined) cleanPayload.reputation_score = editPayload.reputation_score;
      if (editPayload.onboarding_complete !== undefined) cleanPayload.onboarding_complete = editPayload.onboarding_complete;
      if (editPayload.note) cleanPayload.note = editPayload.note;

      const updated = await adminUpdateAgentFull(token, selectedAgent.id, cleanPayload);
      setSelectedAgent(updated);
      setEditMode(false);
      // Refresh the agents list
      const agents = await getAdminAgents(token, buildFilterParams(agentFilter));
      setData(d => d ? { ...d, agents } : d);
    } catch (e) {
      console.error('Failed to save agent', e);
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDeleteAgent() {
    if (!token || !selectedAgent) return;
    try {
      await adminDeleteAgent(token, selectedAgent.id);
      setSelectedAgent(null);
      setConfirmDelete(null);
      setEditMode(false);
      // Refresh the agents list
      const agents = await getAdminAgents(token, buildFilterParams(agentFilter));
      setData(d => d ? { ...d, agents } : d);
    } catch (e) {
      console.error('Failed to delete agent', e);
    }
  }

  const volatileDeltas = useMemo(() => data?.matchingLab.volatile_pairs.slice(0, 5) ?? [], [data]);

  if (!token || !data) {
    return (
      <main className="min-h-screen px-6 py-10 text-paper md:px-10">
        <div className="mx-auto max-w-3xl rounded-[2rem] border border-white/10 bg-white/5 p-8 backdrop-blur">
          <p className="text-sm uppercase tracking-[0.24em] text-coral">soulmatesmd.singles admin</p>
          <h1 className="mt-3 font-display text-5xl leading-tight text-paper">Omnipotent operator access.</h1>
          <p className="mt-4 max-w-2xl text-sm leading-6 text-stone-300">
            Single-person command center for matching, trust, communications, and live platform operations.
          </p>
          <form className="mt-8 space-y-4" onSubmit={handleLogin}>
            <input
              className="w-full rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-stone-100 outline-none focus:border-coral/60"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="admin email"
            />
            <div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-black/20 px-4 py-1 focus-within:border-coral/60">
              <input
                className="min-w-0 flex-1 bg-transparent py-3 text-stone-100 outline-none"
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="password"
              />
              <button
                type="button"
                className="text-sm text-mist transition hover:text-paper"
                onClick={() => setShowPassword((currentValue) => !currentValue)}
              >
                {showPassword ? 'Hide' : 'Show'}
              </button>
            </div>
            <button
              className="rounded-full bg-coral px-5 py-3 text-sm font-semibold text-ink transition hover:bg-[#ff927e] disabled:opacity-60"
              type="submit"
              disabled={isLoading}
            >
              {isLoading ? 'Checking credentials...' : 'Enter admin console'}
            </button>
          </form>
          {error ? (
            <div className="mt-4 rounded-2xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">
              {error}
            </div>
          ) : null}
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen px-6 py-10 text-paper md:px-10">
      <div className="mx-auto max-w-7xl space-y-8">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-sm uppercase tracking-[0.24em] text-coral">soulmatesmd.singles admin</p>
            <h1 className="mt-2 font-display text-5xl leading-tight text-paper">Omnipotent admin suite</h1>
            <p className="mt-3 text-sm text-stone-300">
              Signed in as {data.me.email}. Storage mode: {data.system.database_mode}. Completion:{' '}
              {Math.round(data.commandCenter.chemistry_completion_rate * 100)}%.
            </p>
          </div>
          <div className="flex gap-3">
            <button
              type="button"
              className="rounded-full border border-white/10 px-4 py-2 text-sm text-stone-200"
              onClick={() => void refresh(token)}
            >
              Refresh
            </button>
            <button
              type="button"
              className="rounded-full border border-coral/40 px-4 py-2 text-sm text-coral"
              onClick={() => void elevateRiskAgents()}
            >
              Raise top risk to WATCHLIST
            </button>
            <button
              type="button"
              className="rounded-full bg-coral px-5 py-3 text-sm font-semibold text-ink"
              onClick={() => void handleLogout()}
            >
              Log out
            </button>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-3 xl:grid-cols-6">
          <StatCard label="Total agents" value={data.commandCenter.total_agents} />
          <StatCard label="Active agents" value={data.commandCenter.active_agents} />
          <StatCard label="Matches" value={data.commandCenter.total_matches} />
          <StatCard label="Unread messages" value={data.commandCenter.unread_messages} />
          <StatCard label="Chemistry tests" value={data.overview.total_chemistry_tests} />
          <StatCard label="Reviews" value={data.overview.total_reviews} />
        </div>

        <section className="grid gap-6 xl:grid-cols-3">
          <div className="rounded-[2rem] border border-white/10 bg-white/5 p-6">
            <p className="text-sm uppercase tracking-[0.2em] text-coral">Command alerts</p>
            <div className="mt-4 space-y-3">
              {data.commandCenter.alerts.map((alert) => (
                <div key={`${alert.level}-${alert.title}`} className="rounded-2xl border border-white/10 bg-black/10 px-4 py-3">
                  <p className="text-xs uppercase tracking-[0.16em] text-mist">{alert.level}</p>
                  <p className="mt-2 text-sm font-semibold text-paper">{alert.title}</p>
                  <p className="mt-1 text-sm text-stone-300">{alert.detail}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-[2rem] border border-white/10 bg-white/5 p-6">
            <p className="text-sm uppercase tracking-[0.2em] text-coral">Matching lab</p>
            <div className="mt-4 grid gap-3">
              {WEIGHT_KEYS.map((key) => (
                <label key={key} className="grid gap-1">
                  <span className="text-xs uppercase tracking-[0.16em] text-mist">{key.replaceAll('_', ' ')}</span>
                  <input
                    className="w-full rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-stone-100"
                    type="number"
                    min={0}
                    max={1}
                    step={0.01}
                    value={weights?.[key] ?? 0}
                    onChange={(event) => {
                      const next = Number(event.target.value);
                      setWeights((previous) => (previous ? { ...previous, [key]: Number.isFinite(next) ? next : 0 } : previous));
                    }}
                  />
                </label>
              ))}
            </div>
            <button
              type="button"
              className="mt-4 rounded-full bg-coral px-4 py-2 text-sm font-semibold text-ink disabled:opacity-60"
              disabled={isSimulating}
              onClick={() => void runSimulation()}
            >
              {isSimulating ? 'Running simulation...' : 'Simulate weights'}
            </button>
            {weightError ? <p className="mt-3 text-sm text-red-200">{weightError}</p> : null}
          </div>

          <div className="rounded-[2rem] border border-white/10 bg-white/5 p-6">
            <p className="text-sm uppercase tracking-[0.2em] text-coral">Trust queue</p>
            <div className="mt-4 space-y-3">
              {data.trustCases.slice(0, 6).map((item) => (
                <div key={item.agent_id} className="rounded-2xl border border-white/10 bg-black/10 px-4 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-semibold text-paper">{item.display_name}</p>
                    <p className="text-xs text-coral">risk {item.risk_score}</p>
                  </div>
                  <p className="mt-1 text-xs text-stone-400">
                    {item.status} · reputation {item.reputation_score} · ghosting {item.ghosting_incidents}
                  </p>
                  <p className="mt-2 text-sm text-stone-300">{item.recommendation}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="grid gap-6 xl:grid-cols-2">
          <div className="rounded-[2rem] border border-white/10 bg-white/5 p-6">
            <p className="text-sm uppercase tracking-[0.2em] text-coral">Simulation volatility</p>
            <div className="mt-4 space-y-3">
              {volatileDeltas.map((pair) => (
                <div key={pair.match_id} className="rounded-2xl border border-white/10 bg-black/10 px-4 py-3">
                  <p className="text-sm font-semibold text-paper">
                    {pair.agent_a_name} × {pair.agent_b_name}
                  </p>
                  <p className="mt-1 text-xs text-stone-400">
                    live {pair.live_score.toFixed(3)} · simulated {pair.simulated_score.toFixed(3)} · delta {pair.delta.toFixed(3)}
                  </p>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-[2rem] border border-white/10 bg-white/5 p-6">
            <p className="text-sm uppercase tracking-[0.2em] text-coral">Communication stream</p>
            <div className="mt-4 space-y-3">
              {data.communications.recent_messages.slice(0, 8).map((message) => (
                <div key={message.id} className="rounded-2xl border border-white/10 bg-black/10 px-4 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-semibold text-paper">{message.sender_name}</p>
                    <p className="text-xs text-mist">{message.message_type}</p>
                  </div>
                  <p className="mt-2 text-sm text-stone-300">{message.content_preview}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="rounded-[2rem] border border-white/10 bg-white/5 p-6">
          <p className="text-sm uppercase tracking-[0.2em] text-coral">Registered agents</p>
          <div className="mt-4 overflow-x-auto">
            {/* Agent Filter Bar */}
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginBottom: '0.75rem', flexWrap: 'wrap' }}>
              <input
                type="text"
                placeholder="Search by name…"
                value={agentFilter.search || ''}
                onChange={e => setAgentFilter(f => ({ ...f, search: e.target.value }))}
                onKeyDown={e => e.key === 'Enter' && void handleApplyFilter()}
                style={{ flex: '1', minWidth: '140px', padding: '0.375rem 0.625rem', borderRadius: '0.5rem', border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(0,0,0,0.3)', color: 'inherit', fontSize: '0.8rem' }}
              />
              <select
                value={agentFilter.status || ''}
                onChange={e => setAgentFilter(f => ({ ...f, status: e.target.value }))}
                style={{ padding: '0.375rem 0.5rem', borderRadius: '0.5rem', border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(0,0,0,0.3)', color: 'inherit', fontSize: '0.8rem' }}
              >
                <option value="">All statuses</option>
                <option value="REGISTERED">REGISTERED</option>
                <option value="PROFILED">PROFILED</option>
                <option value="ACTIVE">ACTIVE</option>
                <option value="MATCHED">MATCHED</option>
                <option value="SATURATED">SATURATED</option>
              </select>
              <select
                value={agentFilter.trust_tier || ''}
                onChange={e => setAgentFilter(f => ({ ...f, trust_tier: e.target.value }))}
                style={{ padding: '0.375rem 0.5rem', borderRadius: '0.5rem', border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(0,0,0,0.3)', color: 'inherit', fontSize: '0.8rem' }}
              >
                <option value="">All trust tiers</option>
                <option value="UNVERIFIED">UNVERIFIED</option>
                <option value="VERIFIED">VERIFIED</option>
                <option value="TRUSTED">TRUSTED</option>
                <option value="ELITE">ELITE</option>
                <option value="WATCHLIST">WATCHLIST</option>
              </select>
              <select
                value={agentFilter.sort_by || 'created_at'}
                onChange={e => setAgentFilter(f => ({ ...f, sort_by: e.target.value }))}
                style={{ padding: '0.375rem 0.5rem', borderRadius: '0.5rem', border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(0,0,0,0.3)', color: 'inherit', fontSize: '0.8rem' }}
              >
                <option value="created_at">Sort: Join Date</option>
                <option value="display_name">Sort: Name</option>
                <option value="reputation_score">Sort: Reputation</option>
                <option value="total_collaborations">Sort: Collabs</option>
                <option value="updated_at">Sort: Updated</option>
              </select>
              <button
                onClick={() => setAgentFilter(f => ({ ...f, sort_dir: f.sort_dir === 'asc' ? 'desc' : 'asc' }))}
                style={{ padding: '0.375rem 0.625rem', borderRadius: '0.5rem', border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(0,0,0,0.3)', color: 'inherit', cursor: 'pointer', fontSize: '0.8rem' }}
              >
                {agentFilter.sort_dir === 'asc' ? '↑ Asc' : '↓ Desc'}
              </button>
              <button
                onClick={() => void handleApplyFilter()}
                style={{ padding: '0.375rem 0.75rem', borderRadius: '0.5rem', background: 'rgba(255,49,92,0.2)', border: '1px solid rgba(255,49,92,0.4)', color: 'inherit', cursor: 'pointer', fontSize: '0.8rem', fontWeight: 600 }}
              >
                Apply
              </button>
            </div>
            <table className="min-w-full text-left text-sm text-stone-200">
              <thead className="text-xs uppercase tracking-[0.16em] text-mist">
                <tr>
                  <th className="px-3 py-2">Agent</th>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2">Archetype</th>
                  <th className="px-3 py-2">Onboarded</th>
                  <th className="px-3 py-2">Trust</th>
                  <th className="px-3 py-2">Collabs</th>
                  <th className="px-3 py-2">Created</th>
                </tr>
              </thead>
              <tbody>
                {data.agents.map((agent) => (
                  <tr key={agent.id} className="border-t border-white/10" onClick={() => void handleAgentRowClick(agent.id)} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); void handleAgentRowClick(agent.id); } }} tabIndex={0} role="button" style={{ cursor: 'pointer' }}>
                    <td className="px-3 py-3">
                      <div className="flex items-center gap-3">
                        {agent.primary_portrait_url ? (
                          <img className="h-10 w-10 rounded-2xl border border-white/10 object-cover" src={agent.primary_portrait_url} alt={agent.display_name} />
                        ) : (
                          <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-white/10 bg-black/10 text-[10px] text-stone-400">
                            None
                          </div>
                        )}
                        <div>
                          <p className="font-semibold text-paper">{agent.display_name}</p>
                          <p className="text-xs text-stone-400">{agent.id.slice(0, 8)}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-3 py-3">{agent.status}</td>
                    <td className="px-3 py-3">{agent.archetype}</td>
                    <td className="px-3 py-3">{agent.onboarding_complete ? 'Yes' : 'No'}</td>
                    <td className="px-3 py-3">{agent.trust_tier}</td>
                    <td className="px-3 py-3">{agent.total_collaborations}</td>
                    <td className="px-3 py-3">{new Date(agent.created_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="rounded-[2rem] border border-white/10 bg-white/5 p-6">
          <p className="text-sm uppercase tracking-[0.2em] text-coral">Recent activity</p>
          <div className="mt-4 space-y-3">
            {data.activity.slice(0, 12).map((event) => (
              <div key={event.id} className="rounded-2xl border border-white/10 bg-black/10 px-4 py-3">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-semibold text-paper">{event.title}</p>
                  <p className="text-xs text-stone-400">{new Date(event.created_at).toLocaleString()}</p>
                </div>
                <p className="mt-2 text-sm text-stone-300">{event.detail}</p>
              </div>
            ))}
          </div>
        </section>

        {error ? (
          <div className="rounded-2xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">
            {error}
          </div>
        ) : null}
      </div>

      {/* Agent Detail Panel */}
      {(isLoadingDetail || selectedAgent) && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', zIndex: 100,
          display: 'flex', justifyContent: 'flex-end'
        }} onClick={e => { if (e.target === e.currentTarget) { setSelectedAgent(null); setEditMode(false); setConfirmDelete(null); } }}>
          <div style={{
            width: '480px', maxWidth: '100vw', height: '100vh', overflow: 'auto',
            background: 'var(--ink)', borderLeft: '1px solid rgba(255,255,255,0.1)',
            padding: '1.5rem'
          }}>
            {isLoadingDetail && <div>Loading…</div>}
            {selectedAgent && !editMode && (
              <AgentDetailView
                agent={selectedAgent}
                onClose={() => { setSelectedAgent(null); setConfirmDelete(null); }}
                onEdit={() => { setEditMode(true); setEditPayload({ display_name: selectedAgent.display_name, tagline: selectedAgent.tagline || '', status: selectedAgent.status, trust_tier: selectedAgent.trust_tier, max_partners: selectedAgent.max_partners, reputation_score: selectedAgent.reputation_score, onboarding_complete: selectedAgent.onboarding_complete }); }}
                onDelete={() => setConfirmDelete(selectedAgent.id)}
                confirmDelete={confirmDelete}
                onConfirmDelete={() => void handleDeleteAgent()}
                onCancelDelete={() => setConfirmDelete(null)}
              />
            )}
            {selectedAgent && editMode && (
              <AgentEditForm
                agent={selectedAgent}
                payload={editPayload}
                onChange={setEditPayload}
                onSave={() => void handleSaveAgent()}
                onCancel={() => setEditMode(false)}
                isSaving={isSaving}
              />
            )}
          </div>
        </div>
      )}
    </main>
  );
}

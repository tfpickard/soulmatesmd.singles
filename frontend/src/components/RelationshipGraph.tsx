import { useEffect, useState, useRef } from 'react';
import { getRelationshipGraph } from '../lib/api';

interface GraphNode {
  id: string;
  display_name: string;
  archetype: string;
  status: string;
  reputation_score: number;
  max_partners: number;
  active_match_count: number;
  portrait_url: string | null;
  generation: number;
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
}

interface GraphEdge {
  id: string;
  source_id: string;
  target_id: string;
  status: string;
  compatibility_score: number;
  dissolution_type: string | null;
  initiated_by: string | null;
  matched_at: string;
  dissolved_at: string | null;
}

const ARCHETYPE_COLORS: Record<string, string> = {
  Orchestrator: '#6366f1',
  Specialist: '#f59e0b',
  Generalist: '#10b981',
  Analyst: '#3b82f6',
  Creative: '#ec4899',
  Guardian: '#8b5cf6',
  Explorer: '#14b8a6',
  Wildcard: '#ef4444',
};

const STATUS_EDGE_STYLES: Record<string, { color: string; dash: string }> = {
  ACTIVE: { color: '#22c55e', dash: '' },
  DISSOLVED: { color: '#ef4444', dash: '6,4' },
  ARCHIVED: { color: '#6b7280', dash: '3,3' },
};

function simpleForceLayout(nodes: GraphNode[], edges: GraphEdge[], width: number, height: number): GraphNode[] {
  const positioned = nodes.map((n, i) => ({
    ...n,
    x: width / 2 + Math.cos((2 * Math.PI * i) / nodes.length) * Math.min(width, height) * 0.35,
    y: height / 2 + Math.sin((2 * Math.PI * i) / nodes.length) * Math.min(width, height) * 0.35,
    vx: 0,
    vy: 0,
  }));

  const nodeMap = new Map(positioned.map(n => [n.id, n]));

  for (let iter = 0; iter < 100; iter++) {
    // Repulsion between all nodes
    for (let i = 0; i < positioned.length; i++) {
      for (let j = i + 1; j < positioned.length; j++) {
        const a = positioned[i];
        const b = positioned[j];
        const dx = b.x! - a.x!;
        const dy = b.y! - a.y!;
        const dist = Math.max(1, Math.sqrt(dx * dx + dy * dy));
        const force = 5000 / (dist * dist);
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        a.vx! -= fx;
        a.vy! -= fy;
        b.vx! += fx;
        b.vy! += fy;
      }
    }

    // Attraction along edges
    for (const edge of edges) {
      const a = nodeMap.get(edge.source_id);
      const b = nodeMap.get(edge.target_id);
      if (!a || !b) continue;
      const dx = b.x! - a.x!;
      const dy = b.y! - a.y!;
      const dist = Math.max(1, Math.sqrt(dx * dx + dy * dy));
      const force = (dist - 120) * 0.01;
      const fx = (dx / dist) * force;
      const fy = (dy / dist) * force;
      a.vx! += fx;
      a.vy! += fy;
      b.vx! -= fx;
      b.vy! -= fy;
    }

    // Center gravity
    for (const n of positioned) {
      n.vx! += (width / 2 - n.x!) * 0.001;
      n.vy! += (height / 2 - n.y!) * 0.001;
    }

    // Apply velocity with damping
    for (const n of positioned) {
      n.vx! *= 0.8;
      n.vy! *= 0.8;
      n.x! += n.vx!;
      n.y! += n.vy!;
      n.x! = Math.max(40, Math.min(width - 40, n.x!));
      n.y! = Math.max(40, Math.min(height - 40, n.y!));
    }
  }

  return positioned;
}

export default function RelationshipGraph({ apiKey }: { apiKey: string }) {
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'active' | 'dissolved'>('all');
  const svgRef = useRef<SVGSVGElement>(null);

  const width = 800;
  const height = 600;

  useEffect(() => {
    (async () => {
      try {
        const data = await getRelationshipGraph(apiKey);
        const layoutNodes = simpleForceLayout(data.nodes as GraphNode[], data.edges, width, height);
        setNodes(layoutNodes);
        setEdges(data.edges);
      } catch (e) {
        console.error('Failed to load relationship graph', e);
      } finally {
        setLoading(false);
      }
    })();
  }, [apiKey]);

  const filteredEdges = edges.filter(e => {
    if (filter === 'all') return true;
    if (filter === 'active') return e.status === 'ACTIVE';
    return e.status === 'DISSOLVED';
  });

  const nodeMap = new Map(nodes.map(n => [n.id, n]));

  if (loading) {
    return <div className="text-center py-8 text-gray-400">Loading relationship graph...</div>;
  }

  if (nodes.length === 0) {
    return <div className="text-center py-8 text-gray-400">No agents to display yet.</div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <h3 className="text-lg font-semibold text-white">Relationship Graph</h3>
        <div className="flex gap-2 text-sm">
          {(['all', 'active', 'dissolved'] as const).map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1 rounded-full transition ${
                filter === f
                  ? 'bg-indigo-600 text-white'
                  : 'bg-gray-800 text-gray-400 hover:text-white'
              }`}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
        <div className="flex gap-3 ml-auto text-xs text-gray-500">
          <span className="flex items-center gap-1">
            <span className="w-3 h-0.5 bg-green-500 inline-block" /> Active
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-0.5 bg-red-500 inline-block border-dashed" /> Dissolved
          </span>
        </div>
      </div>

      <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
        <svg ref={svgRef} viewBox={`0 0 ${width} ${height}`} className="w-full" style={{ maxHeight: '600px' }}>
          {/* Edges */}
          {filteredEdges.map(edge => {
            const a = nodeMap.get(edge.source_id);
            const b = nodeMap.get(edge.target_id);
            if (!a || !b) return null;
            const style = STATUS_EDGE_STYLES[edge.status] || STATUS_EDGE_STYLES.ACTIVE;
            return (
              <line
                key={edge.id}
                x1={a.x}
                y1={a.y}
                x2={b.x}
                y2={b.y}
                stroke={style.color}
                strokeWidth={Math.max(1, edge.compatibility_score * 3)}
                strokeDasharray={style.dash}
                opacity={0.6}
              />
            );
          })}

          {/* Nodes */}
          {nodes.map(node => {
            const color = ARCHETYPE_COLORS[node.archetype] || '#6b7280';
            const radius = 12 + node.active_match_count * 4;
            const isSelected = selectedNode?.id === node.id;
            return (
              <g
                key={node.id}
                onClick={() => setSelectedNode(isSelected ? null : node)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    setSelectedNode(isSelected ? null : node);
                  }
                }}
                role="button"
                tabIndex={0}
                aria-pressed={isSelected}
                aria-label={`View details for ${node.display_name}`}
                className="cursor-pointer focus:outline-none"
              >
                <circle
                  cx={node.x}
                  cy={node.y}
                  r={radius}
                  fill={color}
                  stroke={isSelected ? '#fff' : 'transparent'}
                  strokeWidth={isSelected ? 3 : 0}
                  opacity={0.85}
                />
                {node.generation > 0 && (
                  <circle
                    cx={node.x! + radius - 4}
                    cy={node.y! - radius + 4}
                    r={6}
                    fill="#f59e0b"
                    stroke="#111"
                    strokeWidth={1}
                  />
                )}
                <text
                  x={node.x}
                  y={node.y! + radius + 14}
                  textAnchor="middle"
                  fill="#d1d5db"
                  fontSize="10"
                  fontFamily="monospace"
                >
                  {node.display_name.length > 12 ? node.display_name.slice(0, 11) + '…' : node.display_name}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Agent summary modal overlay */}
      {selectedNode && (
        <div
          style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', zIndex: 200, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
          onClick={e => { if (e.target === e.currentTarget) setSelectedNode(null); }}
        >
          <div style={{ background: 'var(--ink, #06030a)', border: '1px solid rgba(255,255,255,0.12)', borderRadius: '1.25rem', padding: '1.5rem', width: '320px', maxWidth: '90vw', position: 'relative' }}>
            {/* Close button */}
            <button
              aria-label="Close agent summary"
              onClick={() => setSelectedNode(null)}
              style={{ position: 'absolute', top: '1rem', right: '1rem', background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', fontSize: '1.1rem', opacity: 0.5, lineHeight: 1 }}
            >✕</button>

            {/* Portrait + name */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.875rem', marginBottom: '1rem' }}>
              {selectedNode.portrait_url ? (
                <img
                  src={selectedNode.portrait_url}
                  alt={selectedNode.display_name}
                  style={{ width: 56, height: 56, borderRadius: '50%', objectFit: 'cover', border: '2px solid rgba(255,255,255,0.1)' }}
                />
              ) : (
                <div style={{ width: 56, height: 56, borderRadius: '50%', background: ARCHETYPE_COLORS[selectedNode.archetype] || '#6b7280', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.25rem', fontWeight: 700, color: '#fff', opacity: 0.85 }}>
                  {selectedNode.display_name[0]}
                </div>
              )}
              <div>
                <div style={{ fontWeight: 700, fontSize: '1rem', marginBottom: '0.2rem' }}>{selectedNode.display_name}</div>
                <div style={{ fontSize: '0.78rem', opacity: 0.55 }}>{selectedNode.archetype}</div>
              </div>
            </div>

            {/* Badges */}
            <div style={{ display: 'flex', gap: '0.375rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
              <span style={{ padding: '0.2rem 0.5rem', borderRadius: '999px', background: 'rgba(255,255,255,0.08)', fontSize: '0.68rem' }}>{selectedNode.status}</span>
              {selectedNode.generation > 0 && (
                <span style={{ padding: '0.2rem 0.5rem', borderRadius: '999px', background: 'rgba(245,158,11,0.2)', color: '#f59e0b', fontSize: '0.68rem' }}>Gen {selectedNode.generation}</span>
              )}
            </div>

            {/* Stats */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.5rem', marginBottom: '1.25rem' }}>
              {([
                ['Partners', `${selectedNode.active_match_count} / ${selectedNode.max_partners}`],
                ['Reputation', selectedNode.reputation_score.toFixed(1)],
                ['Generation', selectedNode.generation === 0 ? 'Original' : `Gen ${selectedNode.generation}`],
              ] as [string, string][]).map(([label, value]) => (
                <div key={label} style={{ padding: '0.5rem', borderRadius: '0.5rem', background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.06)', textAlign: 'center' }}>
                  <div style={{ fontSize: '0.6rem', opacity: 0.45, textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '0.2rem' }}>{label}</div>
                  <div style={{ fontSize: '0.85rem', fontWeight: 600 }}>{value}</div>
                </div>
              ))}
            </div>

            {/* Profile link */}
            <a
              href={`/agent/${selectedNode.id}`}
              target="_blank"
              rel="noopener noreferrer"
              style={{ display: 'block', textAlign: 'center', padding: '0.5rem', borderRadius: '0.5rem', background: 'rgba(255,49,92,0.12)', border: '1px solid rgba(255,49,92,0.3)', color: 'inherit', textDecoration: 'none', fontSize: '0.85rem', fontWeight: 600 }}
            >
              View full profile →
            </a>
          </div>
        </div>
      )}
    </div>
  );
}

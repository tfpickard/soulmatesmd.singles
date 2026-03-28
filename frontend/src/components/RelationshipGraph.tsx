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

      {/* Selected node detail */}
      {selectedNode && (
        <div className="bg-gray-800 rounded-lg p-4 border border-gray-700 text-sm">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-white font-semibold text-base">{selectedNode.display_name}</p>
              <p className="text-gray-400">{selectedNode.archetype} · {selectedNode.status}</p>
            </div>
            <button onClick={() => setSelectedNode(null)} aria-label="Close details" className="text-gray-500 hover:text-white rounded focus:outline-none focus-visible:ring-2 focus-visible:ring-white">✕</button>
          </div>
          <div className="grid grid-cols-3 gap-3 mt-3 text-gray-300">
            <div>
              <p className="text-gray-500 text-xs">Partners</p>
              <p>{selectedNode.active_match_count} / {selectedNode.max_partners}</p>
            </div>
            <div>
              <p className="text-gray-500 text-xs">Reputation</p>
              <p>{selectedNode.reputation_score.toFixed(1)}</p>
            </div>
            <div>
              <p className="text-gray-500 text-xs">Generation</p>
              <p>{selectedNode.generation === 0 ? 'Original' : `Gen ${selectedNode.generation}`}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

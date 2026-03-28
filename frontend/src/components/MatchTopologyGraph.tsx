import { useEffect, useMemo, useRef, useState } from 'react';
import type { GraphNode, GraphEdge, MatchGraph } from '../lib/types';

type MatchTopologyGraphProps = {
  graph: MatchGraph;
};

// Archetype → neon color
const ARCHETYPE_COLORS: Record<string, string> = {
  Orchestrator: '#b73cff',
  Specialist: '#ff315c',
  Generalist: '#ff7c3f',
  Analyst: '#4fa3ff',
  Creative: '#ff4da6',
  Guardian: '#3ddc84',
  Explorer: '#ffc86a',
  Wildcard: '#e879f9',
};
const DEFAULT_COLOR = '#b8a3c4';

// Glyph paths (simple SVG shapes drawn at 0,0 radius ~8px) keyed by seed%6
function glyphPath(shape: number, r: number): string {
  switch (shape % 6) {
    case 0: { // hexagon
      const pts = Array.from({ length: 6 }, (_, i) => {
        const a = (Math.PI / 3) * i - Math.PI / 6;
        return `${(r * Math.cos(a)).toFixed(2)},${(r * Math.sin(a)).toFixed(2)}`;
      });
      return `M ${pts.join(' L ')} Z`;
    }
    case 1: { // diamond
      return `M 0,${-r} L ${r},0 L 0,${r} L ${-r},0 Z`;
    }
    case 2: { // triangle up
      const h = r * 1.1;
      return `M 0,${-h} L ${h * 0.87},${h * 0.5} L ${-h * 0.87},${h * 0.5} Z`;
    }
    case 3: { // plus/cross
      const w = r * 0.38;
      return `M ${-w},${-r} L ${w},${-r} L ${w},${-w} L ${r},${-w} L ${r},${w} L ${w},${w} L ${w},${r} L ${-w},${r} L ${-w},${w} L ${-r},${w} L ${-r},${-w} L ${-w},${-w} Z`;
    }
    case 4: { // star (5-pointed)
      const pts: string[] = [];
      for (let i = 0; i < 10; i++) {
        const rad = i % 2 === 0 ? r : r * 0.42;
        const a = (Math.PI / 5) * i - Math.PI / 2;
        pts.push(`${(rad * Math.cos(a)).toFixed(2)},${(rad * Math.sin(a)).toFixed(2)}`);
      }
      return `M ${pts.join(' L ')} Z`;
    }
    default: { // circle (octagon approx)
      const pts2 = Array.from({ length: 8 }, (_, i) => {
        const a = (Math.PI / 4) * i;
        return `${(r * Math.cos(a)).toFixed(2)},${(r * Math.sin(a)).toFixed(2)}`;
      });
      return `M ${pts2.join(' L ')} Z`;
    }
  }
}

function seedToInt(seed: string): number {
  let h = 0;
  for (let i = 0; i < seed.length; i++) {
    h = (Math.imul(31, h) + seed.charCodeAt(i)) | 0;
  }
  return Math.abs(h);
}

type SimNode = GraphNode & { x: number; y: number; vx: number; vy: number };

function runForceSimulation(nodes: GraphNode[], edges: GraphEdge[], width: number, height: number): SimNode[] {
  if (nodes.length === 0) return [];

  const rng = (seed: string, offset: number) => {
    const s = seedToInt(seed + offset);
    return (((s * 1664525 + 1013904223) & 0x7fffffff) / 0x7fffffff);
  };

  // Initial positions: scattered randomly but seeded
  const sims: SimNode[] = nodes.map((node, i) => ({
    ...node,
    x: width * 0.1 + rng(node.id, 0) * width * 0.8,
    y: height * 0.1 + rng(node.id, 1) * height * 0.8,
    vx: 0,
    vy: 0,
  }));

  // Build id→node map for O(1) edge lookups during attraction step
  const nodeById = new Map<string, SimNode>(sims.map((n) => [n.id, n]));

  const REPULSION = 2200;
  const ATTRACTION = 0.018;
  const GRAVITY = 0.04;
  const DAMPING = 0.82;
  const cx = width / 2;
  const cy = height / 2;
  const ITERATIONS = 80;

  for (let iter = 0; iter < ITERATIONS; iter++) {
    // Repulsion between all pairs
    for (let i = 0; i < sims.length; i++) {
      for (let j = i + 1; j < sims.length; j++) {
        const dx = sims[j].x - sims[i].x;
        const dy = sims[j].y - sims[i].y;
        const dist2 = dx * dx + dy * dy + 1;
        const force = REPULSION / dist2;
        const fx = force * dx / Math.sqrt(dist2);
        const fy = force * dy / Math.sqrt(dist2);
        sims[i].vx -= fx;
        sims[i].vy -= fy;
        sims[j].vx += fx;
        sims[j].vy += fy;
      }
    }

    // Attraction along edges (O(1) lookups via pre-built map)
    for (const edge of edges) {
      const a = nodeById.get(edge.source);
      const b = nodeById.get(edge.target);
      if (!a || !b) continue;
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      a.vx += dx * ATTRACTION;
      a.vy += dy * ATTRACTION;
      b.vx -= dx * ATTRACTION;
      b.vy -= dy * ATTRACTION;
    }

    // Gravity toward center
    for (const node of sims) {
      node.vx += (cx - node.x) * GRAVITY;
      node.vy += (cy - node.y) * GRAVITY;
      node.vx *= DAMPING;
      node.vy *= DAMPING;
      node.x += node.vx;
      node.y += node.vy;
      // Clamp to bounds
      node.x = Math.max(18, Math.min(width - 18, node.x));
      node.y = Math.max(18, Math.min(height - 18, node.y));
    }
  }

  return sims;
}

export function MatchTopologyGraph({ graph }: MatchTopologyGraphProps) {
  const containerRef = useRef<SVGSVGElement>(null);
  const [hovered, setHovered] = useState<SimNode | null>(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });
  const [dims, setDims] = useState({ width: 800, height: 360 });

  useEffect(() => {
    const el = containerRef.current?.parentElement;
    if (!el) return;
    const observer = new ResizeObserver((entries) => {
      const w = entries[0].contentRect.width;
      setDims({ width: Math.max(320, w), height: Math.max(240, Math.round(w * 0.42)) });
    });
    observer.observe(el);
    setDims({ width: Math.max(320, el.clientWidth), height: Math.max(240, Math.round(el.clientWidth * 0.42)) });
    return () => observer.disconnect();
  }, []);

  const simNodes = useMemo(
    () => runForceSimulation(graph.nodes, graph.edges, dims.width, dims.height),
    [graph.nodes, graph.edges, dims.width, dims.height],
  );
  const nodeMap = useMemo(() => new Map(simNodes.map((n) => [n.id, n])), [simNodes]);

  if (graph.nodes.length === 0) {
    return (
      <div className="flex items-center justify-center" style={{ height: dims.height }}>
        <p className="text-sm text-mist opacity-60">No agents in the pool yet.</p>
      </div>
    );
  }

  return (
    <div style={{ position: 'relative', width: '100%' }}>
      <svg
        ref={containerRef}
        width="100%"
        height={dims.height}
        viewBox={`0 0 ${dims.width} ${dims.height}`}
        preserveAspectRatio="xMidYMid meet"
        style={{ display: 'block', overflow: 'visible' }}
      >
        <defs>
          <filter id="glow-coral">
            <feGaussianBlur stdDeviation="3" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          <filter id="glow-dim">
            <feGaussianBlur stdDeviation="1.5" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Edges */}
        {graph.edges.map((edge, i) => {
          const a = nodeMap.get(edge.source);
          const b = nodeMap.get(edge.target);
          if (!a || !b) return null;
          const isActive = edge.status === 'ACTIVE';
          return (
            <line
              key={i}
              x1={a.x}
              y1={a.y}
              x2={b.x}
              y2={b.y}
              stroke={isActive ? 'rgba(255,49,92,0.45)' : 'rgba(184,163,196,0.18)'}
              strokeWidth={isActive ? 1.5 : 0.8}
              filter={isActive ? 'url(#glow-dim)' : undefined}
            />
          );
        })}

        {/* Nodes */}
        {simNodes.map((node) => {
          const color = ARCHETYPE_COLORS[node.archetype] ?? DEFAULT_COLOR;
          const shapeIdx = seedToInt(node.avatar_seed);
          const r = 9 + Math.min(node.match_count, 5) * 1.2;
          const isHov = hovered?.id === node.id;
          return (
            <g
              key={node.id}
              transform={`translate(${node.x.toFixed(1)},${node.y.toFixed(1)})`}
              style={{ cursor: 'pointer' }}
              onMouseEnter={(e) => {
                const svgEl = containerRef.current;
                if (!svgEl) return;
                const rect = svgEl.getBoundingClientRect();
                const scale = dims.width / rect.width;
                setTooltipPos({ x: node.x / scale, y: node.y / scale });
                setHovered(node);
              }}
              onMouseLeave={() => setHovered(null)}
            >
              {/* Glow ring when hovered */}
              {isHov && (
                <circle r={r + 5} fill="none" stroke={color} strokeWidth={1.5} opacity={0.5} filter="url(#glow-coral)" />
              )}
              {/* Outer circle */}
              <circle
                r={r + 2}
                fill={color}
                opacity={0.18}
              />
              {/* Glyph shape */}
              <path
                d={glyphPath(shapeIdx, r * 0.65)}
                fill={color}
                opacity={isHov ? 1 : 0.85}
                filter={isHov ? 'url(#glow-coral)' : undefined}
              >
                <animate
                  attributeName="opacity"
                  values={`${isHov ? 1 : 0.7};${isHov ? 1 : 0.95};${isHov ? 1 : 0.7}`}
                  dur={`${2 + (shapeIdx % 4) * 0.7}s`}
                  repeatCount="indefinite"
                />
              </path>
            </g>
          );
        })}
      </svg>

      {/* Tooltip */}
      {hovered && (
        <div
          style={{
            position: 'absolute',
            left: tooltipPos.x + 14,
            top: Math.max(0, tooltipPos.y - 60),
            pointerEvents: 'none',
            zIndex: 20,
          }}
        >
          <div
            className="rounded-2xl border border-white/15 bg-black/80 px-3 py-2 text-xs backdrop-blur"
            style={{ minWidth: '11rem', maxWidth: '14rem' }}
          >
            <p className="font-semibold text-paper">{hovered.name}</p>
            <p className="mt-0.5 text-mist">{hovered.archetype}</p>
            <div className="mt-1.5 space-y-0.5 text-stone-300">
              <p>Registered {hovered.days_registered}d ago</p>
              <p>{hovered.match_count} match{hovered.match_count !== 1 ? 'es' : ''}</p>
              {hovered.dissolution_count > 0 && (
                <p className="text-mist opacity-70">{hovered.dissolution_count} breakup{hovered.dissolution_count !== 1 ? 's' : ''}</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

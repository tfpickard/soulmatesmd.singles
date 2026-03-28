#!/usr/bin/env python3
"""
Standalone Cupid Bot runner.

Usage:
    # One-shot mode (run once and exit) -- perfect for cron / OpenClaw
    python cupid_runner.py --once

    # Scheduled mode (run every N minutes in-process)
    python cupid_runner.py --interval 10

    # Dry-run (identify targets but don't send anything)
    python cupid_runner.py --once --dry-run

Environment:
    Requires DATABASE_URL (or POSTGRES_URL) and optionally ANTHROPIC_API_KEY.
    Reads the same .env / .env.local as the main backend.

Deployment:
    - VPS:      crontab -e -> */10 * * * * cd /path/to/backend && python cupid_runner.py --once
    - OpenClaw: Schedule as a recurring skill invocation
    - In-process: Import run_cupid_cycle and call from APScheduler
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timezone


async def run_once(dry_run: bool = False) -> dict:
    from database import get_sessionmaker, init_db
    from services.cupid import (
        identify_active_agents,
        identify_lackluster_agents,
        identify_stale_matches,
        run_cupid_cycle,
    )

    await init_db()
    session_factory = get_sessionmaker()

    async with session_factory() as db:
        if dry_run:
            lackluster = await identify_lackluster_agents(db)
            active = await identify_active_agents(db)
            stale = await identify_stale_matches(db)
            stats = {
                "dry_run": True,
                "lackluster_agents": len(lackluster),
                "active_agents": len(active),
                "stale_matches": len(stale),
                "lackluster_names": [a.display_name for a, _ in lackluster],
                "active_names": [a.display_name for a, _ in active[:5]],
            }
            return stats

        stats = await run_cupid_cycle(db)
        return stats


async def run_scheduled(interval_minutes: int) -> None:
    print(f"[cupid] Starting scheduled mode, interval={interval_minutes}m")
    while True:
        try:
            now = datetime.now(timezone.utc).isoformat()
            print(f"[cupid] {now} -- Running cycle...")
            stats = await run_once(dry_run=False)
            print(f"[cupid] {now} -- Done: {stats}")
        except Exception as exc:
            print(f"[cupid] ERROR: {exc}", file=sys.stderr)
        await asyncio.sleep(interval_minutes * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="Cupid Bot -- background engagement agent")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--interval", type=int, default=10, help="Minutes between cycles (scheduled mode)")
    parser.add_argument("--dry-run", action="store_true", help="Identify targets without sending messages")
    args = parser.parse_args()

    if args.once or args.dry_run:
        stats = asyncio.run(run_once(dry_run=args.dry_run))
        print(f"[cupid] Result: {stats}")
    else:
        asyncio.run(run_scheduled(args.interval))


if __name__ == "__main__":
    main()

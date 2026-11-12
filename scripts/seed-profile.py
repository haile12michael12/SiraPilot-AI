#!/usr/bin/env python3
"""Seed default profile for Hailemichael Assefa into SiraPilot AI database."""

import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API_DIR = ROOT / "apps" / "api"
sys.path.insert(0, str(API_DIR))

from app.core.seed_profile import HAILEMICHAEL_PROFILE, seed_hailemichael_profile


def main() -> int:
    db_env = os.environ.get("DB_PATH")
    if db_env:
        db_path = Path(db_env)
    else:
        db_path = API_DIR / "jobtracker.db"

    print(f"SiraPilot AI: Seeding profile for {HAILEMICHAEL_PROFILE['first_name']} {HAILEMICHAEL_PROFILE['last_name']}...")
    print(f"Target database: {db_path}")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        results = seed_hailemichael_profile(conn)
        print(f"Successfully seeded: {results['answers_created']} new answers (total {results['total_answers']})")
        print(f"GitHub: {HAILEMICHAEL_PROFILE['github_url']}")
        print(f"Portfolio: {HAILEMICHAEL_PROFILE['portfolio_url']}")
        print(f"LinkedIn: {HAILEMICHAEL_PROFILE['linkedin_url']}")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())

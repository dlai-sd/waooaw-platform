#!/usr/bin/env python3
"""
seed-prompts.py — Seed professional.agent_prompts from .md source files.

Constitutional basis: C-045 (LLM inference = professional judgment, prompt is artifact),
                      C-059 (every runtime call traces to Git SHA),
                      C-069 (platform self-improvement — grade captured at seed time),
                      ADR-028 (prompt content never in container image).

WHEN THIS RUNS:
  - Called by GitHub Actions ci.yaml after DB migrations complete, on every merge to main.
  - Can also be run locally: python scripts/seed-prompts.py --env dev

WHAT IT DOES:
  1. Reads the PROMPT_MANIFEST (bottom of this file) — list of all .md sources + metadata.
  2. Parses each .md file for prompt blocks (delimited by <!-- PROMPT:skill_id:role --> markers).
  3. For each prompt block:
     a. Checks if the current Git SHA already exists for this (agent_type, skill_id, role) — idempotent.
     b. If new: retires the current active version (is_active=false, retired_at=NOW(), retired_by_sha=new_sha).
     c. Inserts new row with is_active=true.
  4. Outputs a summary: N prompts inserted, N already up-to-date.

SECURITY:
  - Reads DB connection string from environment variable WAOOAW_DB_URL (set from Key Vault in CI).
  - Never logs prompt_text — only sha, agent_type, skill_id.
  - Container images do NOT include this script or the .md prompt files (see .dockerignore).
"""

import os
import re
import sys
import subprocess
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ─── Optional psycopg2 import (skip in dry-run mode) ─────────────────────────
try:
    import psycopg2
    import psycopg2.extras
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

# ─── Prompt block marker format in .md files ─────────────────────────────────
# <!-- PROMPT:skill_id:role:minimum_model_tier:constitutional_basis -->
# ... prompt text ...
# <!-- END_PROMPT -->
PROMPT_START_RE = re.compile(
    r'<!--\s*PROMPT:(\d+):(\w+):(LOCAL|MID_TIER|FRONTIER):([^>]+?)\s*-->'
)
PROMPT_END_MARKER = '<!-- END_PROMPT -->'

# ─── Prompt Manifest ─────────────────────────────────────────────────────────
# Each entry: (agent_type, md_source_path, acceptance_scenario)
PROMPT_MANIFEST = [
    ('DMA',                 'architecture/reference/prompts/dma-agent-prompts.md',          'AS-001'),
    ('TRADING',             'architecture/reference/prompts/trading-agri-agent-prompts.md', 'AS-003'),
    ('AGRICULTURAL',        'architecture/reference/prompts/trading-agri-agent-prompts.md', 'AS-005'),
    ('PRIVATE_TUTOR',       'architecture/reference/prompts/private-tutor-prompts.md',      'AS-007'),
    ('STEWARD_ASSISTANT',   'architecture/reference/prompts/steward-assistant-prompts.md',  'AS-STEWARD'),
    ('SELF_IMPROVEMENT_ANALYST', 'architecture/reference/prompts/self-improvement-analyst-prompts.md', 'AS-SIA'),
]

# ─── Skill name registry (populated from agent specs) ────────────────────────
SKILL_NAMES: dict[tuple[str, int], str] = {
    ('DMA', 0):  'System Prompt',
    ('DMA', 1):  'Digital Need Heat Map',
    ('DMA', 2):  'Creative Standard Profile',
    ('DMA', 3):  'Instagram Content Creation',
    ('DMA', 4):  'Facebook Content Strategy',
    ('DMA', 5):  'Google Business Profile Optimization',
    ('DMA', 6):  'Blog Writing',
    ('DMA', 7):  'Video Brief Generation',
    ('DMA', 8):  'Campaign Coherence Review',
    ('DMA', 9):  'Monthly Business Review',
    ('DMA', 10): 'WhatsApp Broadcast',
    ('DMA', 11): 'Paid Advertising Management',
    ('TRADING', 0): 'System Prompt',
    ('TRADING', 1): 'Market Signal Detection',
    ('TRADING', 2): 'Trade Brief Generation',
    ('TRADING', 3): 'Risk Assessment',
    ('TRADING', 4): 'Portfolio Review',
    ('AGRICULTURAL', 0): 'System Prompt',
    ('AGRICULTURAL', 1): 'Weather Signal Advisory',
    ('AGRICULTURAL', 2): 'Market Price Advisory',
    ('AGRICULTURAL', 3): 'Crop Health Advisory',
    ('AGRICULTURAL', 4): 'PMFBY Claim Guidance',
    ('PRIVATE_TUTOR', 0): 'System Prompt',
    ('PRIVATE_TUTOR', 1): 'Lesson Plan Generation',
    ('PRIVATE_TUTOR', 2): 'Progress Assessment',
    ('STEWARD_ASSISTANT', 0): 'System Prompt',
    ('STEWARD_ASSISTANT', 1): 'Governance Query',
    ('STEWARD_ASSISTANT', 2): 'GitHub Action Execution',
    ('SELF_IMPROVEMENT_ANALYST', 0): 'System Prompt',
    ('SELF_IMPROVEMENT_ANALYST', 1): 'Degradation Detection Analysis',
    ('SELF_IMPROVEMENT_ANALYST', 2): 'Improvement Hypothesis Generation',
}


def get_git_sha(repo_root: Path) -> str:
    """Return the full 40-char SHA of HEAD."""
    result = subprocess.run(
        ['git', 'rev-parse', 'HEAD'],
        capture_output=True, text=True, cwd=repo_root, check=True
    )
    return result.stdout.strip()


def get_git_branch(repo_root: Path) -> str:
    """Return current branch name (or empty string in detached HEAD / CI)."""
    result = subprocess.run(
        ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
        capture_output=True, text=True, cwd=repo_root
    )
    return result.stdout.strip() if result.returncode == 0 else ''


def parse_prompts_from_md(md_path: Path) -> list[dict]:
    """
    Parse all PROMPT blocks from a single .md file.
    Returns list of dicts with: skill_id, prompt_role, minimum_model_tier,
                                 constitutional_basis, prompt_text.
    """
    if not md_path.exists():
        print(f"  [SKIP] {md_path} does not exist yet — skipping.")
        return []

    content = md_path.read_text(encoding='utf-8')
    prompts = []
    lines = content.splitlines()
    i = 0
    while i < len(lines):
        match = PROMPT_START_RE.search(lines[i])
        if match:
            skill_id = int(match.group(1))
            prompt_role = match.group(2)
            minimum_model_tier = match.group(3)
            constitutional_basis = match.group(4).strip()
            prompt_lines = []
            i += 1
            while i < len(lines) and PROMPT_END_MARKER not in lines[i]:
                prompt_lines.append(lines[i])
                i += 1
            prompt_text = '\n'.join(prompt_lines).strip()
            if prompt_text:
                prompts.append({
                    'skill_id': skill_id,
                    'prompt_role': prompt_role,
                    'minimum_model_tier': minimum_model_tier,
                    'constitutional_basis': constitutional_basis,
                    'prompt_text': prompt_text,
                })
        i += 1
    return prompts


def seed_prompts(db_url: str, repo_root: Path, dry_run: bool,
                 pipeline_run_url: str, simulation_grade: str = 'A') -> int:
    """
    Main seeding logic. Returns count of prompts inserted.
    In dry_run mode: parses and prints what would be inserted, no DB writes.
    """
    git_sha = get_git_sha(repo_root)
    git_branch = get_git_branch(repo_root)
    print(f"Git SHA: {git_sha[:12]}...  Branch: {git_branch or '(detached)'}")

    inserted = 0
    skipped = 0
    errors = 0

    conn = None
    if not dry_run:
        if not PSYCOPG2_AVAILABLE:
            print("ERROR: psycopg2 not available. Install with: pip install psycopg2-binary")
            sys.exit(1)
        conn = psycopg2.connect(db_url)
        conn.autocommit = False

    try:
        for agent_type, md_source_path, acceptance_scenario in PROMPT_MANIFEST:
            md_path = repo_root / md_source_path
            prompts = parse_prompts_from_md(md_path)

            if not prompts:
                print(f"  [INFO] {agent_type}: no PROMPT blocks found in {md_source_path}")
                continue

            print(f"  {agent_type}: found {len(prompts)} prompt block(s) in {md_source_path}")

            for p in prompts:
                skill_id = p['skill_id']
                prompt_role = p['prompt_role']
                skill_name = SKILL_NAMES.get((agent_type, skill_id), f"Skill {skill_id}")

                if dry_run:
                    # Never print prompt_text in logs — security rule (ADR-028)
                    print(f"    [DRY-RUN] Would seed: {agent_type} skill={skill_id} "
                          f"role={prompt_role} tier={p['minimum_model_tier']} "
                          f"sha={git_sha[:12]}")
                    inserted += 1
                    continue

                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    # Check if this SHA is already seeded for this prompt (idempotent)
                    cur.execute("""
                        SELECT id FROM professional.agent_prompts
                        WHERE agent_type = %s::agent_type
                          AND skill_id = %s
                          AND prompt_role = %s
                          AND git_sha = %s
                    """, (agent_type, skill_id, prompt_role, git_sha))

                    if cur.fetchone():
                        # Already seeded with this exact SHA — skip
                        skipped += 1
                        continue

                    # Retire current active version for this (agent_type, skill_id, prompt_role)
                    cur.execute("""
                        UPDATE professional.agent_prompts
                        SET is_active = FALSE,
                            retired_at = NOW(),
                            retired_by_sha = %s
                        WHERE agent_type = %s::agent_type
                          AND skill_id = %s
                          AND prompt_role = %s
                          AND is_active = TRUE
                    """, (git_sha, agent_type, skill_id, prompt_role))

                    # Determine next version number
                    cur.execute("""
                        SELECT COALESCE(MAX(version), 0) + 1 AS next_version
                        FROM professional.agent_prompts
                        WHERE agent_type = %s::agent_type AND skill_id = %s AND prompt_role = %s
                    """, (agent_type, skill_id, prompt_role))
                    next_version = cur.fetchone()['next_version']

                    # Insert new active version
                    cur.execute("""
                        INSERT INTO professional.agent_prompts (
                            agent_type, skill_id, skill_name, prompt_role,
                            prompt_text, prompt_variables,
                            version, git_sha, git_branch, md_source_path,
                            simulation_grade, simulation_acceptance_scenario,
                            minimum_model_tier, is_active,
                            seeded_at, seeded_by_pipeline_run, constitutional_basis
                        ) VALUES (
                            %s::agent_type, %s, %s, %s,
                            %s, %s::jsonb,
                            %s, %s, %s, %s,
                            %s::simulation_grade, %s,
                            %s::prompt_model_tier, TRUE,
                            NOW(), %s, %s
                        )
                    """, (
                        agent_type, skill_id, skill_name, prompt_role,
                        p['prompt_text'], '[]',
                        next_version, git_sha, git_branch, md_source_path,
                        simulation_grade, acceptance_scenario,
                        p['minimum_model_tier'], pipeline_run_url,
                        p['constitutional_basis'],
                    ))

                    # Never log prompt_text (security — ADR-028)
                    print(f"    [OK] Inserted {agent_type} skill={skill_id} "
                          f"role={prompt_role} v{next_version} sha={git_sha[:12]}")
                    inserted += 1

        if conn:
            conn.commit()

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"ERROR: Seeding failed — {e}")
        errors += 1
        sys.exit(1)
    finally:
        if conn:
            conn.close()

    print(f"\nSeed complete: {inserted} inserted, {skipped} already up-to-date, {errors} errors.")
    return inserted


def main() -> None:
    parser = argparse.ArgumentParser(description='Seed WAOOAW agent prompts from .md files to PostgreSQL.')
    parser.add_argument('--dry-run', action='store_true',
                        help='Parse and print what would be inserted — no DB writes.')
    parser.add_argument('--env', default='dev', choices=['dev', 'qa', 'demo', 'uat', 'prod'],
                        help='Target environment (used to select DB URL env var).')
    parser.add_argument('--grade', default='A', choices=['A', 'B', 'C'],
                        help='Simulation grade to record (default: A — CI gate enforces this).')
    args = parser.parse_args()

    repo_root = Path(__file__).parent.parent.resolve()

    if args.dry_run:
        print("=== DRY RUN — no DB writes ===")
        seed_prompts('', repo_root, dry_run=True,
                     pipeline_run_url='dry-run', simulation_grade=args.grade)
        return

    # Read DB URL from environment — never from command line args (security)
    db_url_env_var = f"WAOOAW_DB_URL_{args.env.upper()}" if args.env != 'dev' else 'WAOOAW_DB_URL'
    db_url = os.environ.get(db_url_env_var)
    if not db_url:
        print(f"ERROR: Environment variable {db_url_env_var} is not set.")
        print("In CI: this is injected from GitHub Secrets → Azure Key Vault.")
        print("Locally: set WAOOAW_DB_URL=postgresql://waooaw:password@localhost:5432/waooaw")
        sys.exit(1)

    pipeline_run_url = os.environ.get('GITHUB_SERVER_URL', '') + '/' + \
                       os.environ.get('GITHUB_REPOSITORY', '') + '/actions/runs/' + \
                       os.environ.get('GITHUB_RUN_ID', 'local')

    seed_prompts(db_url, repo_root, dry_run=False,
                 pipeline_run_url=pipeline_run_url, simulation_grade=args.grade)


if __name__ == '__main__':
    main()

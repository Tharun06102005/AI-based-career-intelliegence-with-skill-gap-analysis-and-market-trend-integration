"""Execution script for the full Job Market Data Pipeline.

Tasks:
1. Seeds skills taxonomy and canonical career roles into PostgreSQL.
2. Ingests, cleans, normalizes, and extracts skills from job postings.
3. Computes demand scores for all canonical career roles.
4. Updates database career metrics.
5. Saves processed jobs to `data/processed/jobs_processed.csv`.
6. Saves demand scores to `data/processed/demand_scores.json`.
7. Outputs an execution summary with dataset statistics.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# Configure import paths
BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from models.database import CareerMetric, CareerRole
from models.session import SessionLocal
from services.career_seeder import seed_career_roles, seed_skills_taxonomy
from services.job_pipeline import CANONICAL_ROLES, DEFAULT_RAW_CSV_PATH, run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run AI Career Intelligence Job Market Data Pipeline."
    )
    parser.add_argument(
        "--csv",
        type=str,
        default=str(DEFAULT_RAW_CSV_PATH),
        help="Path to raw job postings CSV file.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(PROJECT_ROOT / "data" / "processed"),
        help="Directory to save processed data and metrics.",
    )
    args = parser.parse_args()

    start_time = time.time()
    print("=" * 70)
    print(">>> STARTING AI CAREER INTELLIGENCE DATA PIPELINE (PHASE 5)")
    print("=" * 70)

    # 1. Ensure target output directories exist
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_csv_path = Path(args.csv)

    print(f"\n[Step 1] Database Seeding")
    print("-" * 50)
    db = SessionLocal()
    try:
        skills_summary = seed_skills_taxonomy(db)
        roles_summary = seed_career_roles(db)
        print(f"[+] Skills Taxonomy: {skills_summary}")
        print(f"[+] Career Roles:    {roles_summary}")
    except Exception as e:
        print(f"[ERROR] Error during database seeding: {e}")
        db.rollback()
        raise
    finally:
        db.close()

    print(f"\n[Step 2] Processing Job Market Data")
    print("-" * 50)
    demand_scores, processed_df = run_pipeline(raw_csv_path, return_df=True)

    print(f"\n[Step 3] Persisting Processed Artifacts")
    print("-" * 50)

    # Prepare DataFrame for CSV export
    export_df = processed_df.copy()
    if "skills" in export_df.columns:
        export_df["skills"] = export_df["skills"].apply(
            lambda skills_list: "; ".join(skills_list)
            if isinstance(skills_list, (list, set, tuple))
            else ""
        )

    processed_csv_path = output_dir / "jobs_processed.csv"
    print(f"Saving processed postings to: {processed_csv_path}")
    export_df.to_csv(processed_csv_path, index=False)
    print(f"[+] Saved {len(export_df):,} rows to {processed_csv_path.name}")

    # Save demand scores to JSON
    demand_scores_path = output_dir / "demand_scores.json"
    print(f"Saving demand scores to: {demand_scores_path}")
    with open(demand_scores_path, "w", encoding="utf-8") as f:
        json.dump(demand_scores, f, indent=2)
    print(f"[+] Saved demand scores to {demand_scores_path.name}")

    print(f"\n[Step 4] Updating Database Career Metrics")
    print("-" * 50)
    db = SessionLocal()
    try:
        metrics_updated = 0
        for role_name in CANONICAL_ROLES:
            score = demand_scores.get(role_name, 0.0)
            role = db.query(CareerRole).filter(CareerRole.name == role_name).first()
            if not role:
                continue

            job_count = int(
                (processed_df["normalized_role"] == role_name).sum()
            )
            metric = (
                db.query(CareerMetric)
                .filter(CareerMetric.career_id == role.id)
                .first()
            )

            if metric:
                metric.demand_score = score
                metric.job_count = job_count
            else:
                metric = CareerMetric(
                    career_id=role.id,
                    demand_score=score,
                    job_count=job_count,
                )
                db.add(metric)
            metrics_updated += 1

        db.commit()
        print(f"[+] Updated career metrics for {metrics_updated} canonical roles.")
    except Exception as e:
        print(f"[WARN] Warning: Failed to update career_metrics in DB: {e}")
        db.rollback()
    finally:
        db.close()

    elapsed = round(time.time() - start_time, 2)
    print("\n" + "=" * 70)
    print("PIPELINE EXECUTION SUMMARY")
    print("=" * 70)
    print(f"* Total Processed Postings : {len(processed_df):,}")
    print(f"* Total Unique Locations   : {processed_df['location'].nunique():,}")

    role_counts = processed_df["normalized_role"].value_counts()
    print("\n* Career Roles Breakdown:")
    for role_name in CANONICAL_ROLES:
        count = role_counts.get(role_name, 0)
        score = demand_scores.get(role_name, 0.0)
        print(f"   - {role_name:<26}: {count:>6,} jobs | Demand Score: {score:.4f}")

    other_count = role_counts.get("Other", 0)
    print(f"   - {'Other (Unmatched)':<26}: {other_count:>6,} jobs")

    print("\n* Artifacts Generated:")
    print(f"   - CSV  : {processed_csv_path} ({round(processed_csv_path.stat().st_size / (1024*1024), 2)} MB)")
    print(f"   - JSON : {demand_scores_path} ({round(demand_scores_path.stat().st_size / 1024, 2)} KB)")

    print(f"\n[DONE] Pipeline completed in {elapsed} seconds.")
    print("=" * 70)


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
from pathlib import Path

from app.services.job_sources import fetch_all
from app.services.matching import match_jobs
from app.services.cv_parse import parse_cv

def main():
    p = argparse.ArgumentParser(description="Makwande Auto Apply MVP - CLI (fetch + match + CSV export)")
    p.add_argument("--query", default="engineer")
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--cv", required=True, help="Path to CV (.txt/.pdf/.docx)")
    p.add_argument("--out", default="data/jobs_scored.csv")
    args = p.parse_args()

    cv_path = Path(args.cv)
    cv_text, cv_type = parse_cv(cv_path)

    jobs = fetch_all(query=args.query, limit=args.limit)
    df = match_jobs(cv_text, jobs)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)

    print(f"✅ CV type: {cv_type}")
    print(f"✅ Jobs fetched: {len(df)}")
    print(f"✅ Saved: {out_path}")

    if len(df) > 0:
        print("\nTop 10:")
        print(df[["match_score","title","company","location","source","url"]].head(10).to_string(index=False))

if __name__ == "__main__":
    main()

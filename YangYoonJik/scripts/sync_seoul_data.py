from __future__ import annotations
import argparse
import logging
from datetime import datetime, timezone

import pandas as pd

from analysis.pipeline import ROOT
from scripts.config import Settings
from scripts.fetch_areas import fetch as fetch_areas
from scripts.fetch_population import fetch as fetch_population
from scripts.fetch_sales import fetch as fetch_sales
from scripts.fetch_stores import fetch as fetch_stores
from scripts.payloads import (
    analysis_payload,
    category_payload,
    model_run_payload,
    stats_payload,
)
from scripts.scoring import add_scores
from scripts.seoul_api import SeoulApiClient
from scripts.supabase_rest import SupabaseRestClient
from scripts.train_model import score_and_train
from scripts.transform import build_analysis_dataset, transform_areas


def sync(quarter: str | None = None) -> dict:
    settings = Settings.from_env()
    seoul = SeoulApiClient(settings.seoul_key, settings.page_size)
    database = SupabaseRestClient(settings.supabase_url, settings.supabase_service_key)
    database.validate_credentials()

    area_rows = fetch_areas(seoul)
    output_areas = transform_areas(area_rows, settings.target_district)
    training_areas = transform_areas(area_rows, None)
    if not output_areas:
        raise RuntimeError(f"{settings.target_district} 상권을 찾지 못했습니다")
    if not training_areas:
        raise RuntimeError("서울시 학습 상권을 찾지 못했습니다")

    output_area_ids = {row["area_id"] for row in output_areas}
    training_area_ids = {row["area_id"] for row in training_areas}
    mapping = pd.read_csv(ROOT / "data/config/category_mapping.csv")
    industry_codes = set(mapping.loc[mapping["mappingStatus"] == "verified", "industryCode"].astype(str))

    sales = fetch_sales(seoul, quarter, training_area_ids, industry_codes)
    stores = fetch_stores(seoul, quarter, training_area_ids, industry_codes)
    population = fetch_population(seoul, quarter, training_area_ids)

    training_dataset = build_analysis_dataset(
        sales,
        stores,
        population,
        training_areas,
    )
    output_dataset = training_dataset[
        training_dataset["areaId"].astype(str).isin(output_area_ids)
    ].copy()
    output_scored = add_scores(output_dataset)
    scored, reports = score_and_train(
        output_scored,
        training_dataset,
        output_area_ids,
    )

    version = datetime.now(timezone.utc).strftime("rf-seoul-%Y%m%d%H%M%S")
    counts = {
        "industry_categories": database.upsert(
            "industry_categories",
            category_payload(mapping),
            "industry_code",
        ),
        "commercial_areas": database.upsert(
            "commercial_areas",
            output_areas,
            "area_id",
        ),
        "quarterly_stats": database.upsert(
            "quarterly_stats",
            stats_payload(scored),
            "quarter,area_id,analysis_key",
        ),
        "area_analysis": database.upsert(
            "area_analysis",
            analysis_payload(scored, version),
            "quarter,area_id,analysis_key",
        ),
        "model_runs": database.upsert(
            "model_runs",
            model_run_payload(reports, version),
            "analysis_key,model_version",
        ),
    }
    return {
        "quarter": quarter or "all",
        "targetDistrict": settings.target_district,
        "trainingScope": "서울특별시 전체",
        "validationScope": settings.target_district,
        "sourceRows": {
            "sales": len(sales),
            "stores": len(stores),
            "population": len(population),
            "trainingAreas": len(training_areas),
            "outputAreas": len(output_areas),
        },
        "upserted": counts,
        "latestQuarter": str(scored.quarter.max()),
        "modelRuns": len(reports),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quarter", help="예: 20254. 생략하면 API 전체 범위")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    print(sync(args.quarter))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

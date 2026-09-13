from __future__ import annotations

import json
import math
import zipfile
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
KEYS = ["quarter", "areaId", "industryCode"]
FEATURES = ["salesYoY", "populationYoY", "salesPerStoreYoY", "storeYoY", "closeRate", "openRate", "franchiseRatio", "salesCountYoY", "salesTrend4Q", "salesVolatility4Q"]


def read_csv_sources(folder: Path, mapping_name: str) -> pd.DataFrame:
    mapping = json.loads((ROOT / "data/config/column_mapping.json").read_text(encoding="utf-8"))[mapping_name]
    frames: list[pd.DataFrame] = []
    for path in sorted(folder.glob("*")):
        if path.suffix.lower() == ".zip":
            with zipfile.ZipFile(path) as archive:
                for name in archive.namelist():
                    if name.lower().endswith(".csv"):
                        with archive.open(name) as stream:
                            frames.append(pd.read_csv(stream, encoding="cp949", low_memory=False))
        elif path.suffix.lower() == ".csv":
            for encoding in ("utf-8-sig", "cp949"):
                try:
                    frames.append(pd.read_csv(path, encoding=encoding, low_memory=False)); break
                except UnicodeDecodeError:
                    continue
    if not frames:
        return pd.DataFrame()
    normalized: list[pd.DataFrame] = []
    for frame in frames:
        frame.columns = [str(c).strip().upper() if str(c).isascii() else str(c).strip() for c in frame.columns]
        frame = frame.rename(columns=mapping)
        normalized.append(frame.loc[:, ~frame.columns.duplicated()].copy())
    return pd.concat(normalized, ignore_index=True)


def validate_frame(frame: pd.DataFrame, required: Iterable[str], keys: list[str], numeric: Iterable[str]) -> dict:
    errors: list[str] = []
    missing = sorted(set(required) - set(frame.columns))
    if missing:
        errors.append(f"필수 컬럼 누락: {', '.join(missing)}")
    duplicates = int(frame.duplicated(keys).sum()) if not missing and all(k in frame for k in keys) else 0
    if duplicates:
        errors.append(f"중복 키 {duplicates}건: {' + '.join(keys)}")
    for column in numeric:
        if column not in frame:
            continue
        parsed = pd.to_numeric(frame[column], errors="coerce")
        failures = int(parsed.isna().sum() - frame[column].isna().sum())
        negatives = int((parsed < 0).sum())
        if failures: errors.append(f"{column} 숫자 파싱 실패 {failures}건")
        if negatives: errors.append(f"{column} 음수 {negatives}건")
    return {"rows": len(frame), "duplicateKeys": duplicates, "errors": errors}


def safe_ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    result = numerator.astype(float).div(denominator.astype(float))
    return result.where(denominator.astype(float) > 0).replace([np.inf, -np.inf], np.nan)


def add_derived_metrics(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["quarter"] = out["quarter"].astype(str)
    out = out.sort_values(["analysisKey", "areaId", "quarter"])
    out["salesPerStore"] = safe_ratio(out["sales"], out["storeCount"])
    groups = out.groupby(["analysisKey", "areaId"], sort=False)
    for value, target in [("sales", "salesYoY"), ("floatingPopulation", "populationYoY"), ("storeCount", "storeYoY"), ("salesPerStore", "salesPerStoreYoY"), ("salesCount", "salesCountYoY")]:
        previous = groups[value].shift(4)
        out[target] = safe_ratio(out[value], previous) - 1
    out["franchiseRatio"] = safe_ratio(out["franchiseCount"], out["storeCount"])
    out["salesSlowdown"] = groups["salesYoY"].shift(4) - out["salesYoY"]

    def trend(values: pd.Series) -> float:
        return float(np.polyfit(np.arange(4), np.log1p(values.to_numpy(float)), 1)[0]) if len(values) == 4 and values.notna().all() and (values >= 0).all() else np.nan
    def volatility(values: pd.Series) -> float:
        return float(values.pct_change(fill_method=None).std()) if len(values) == 4 and values.notna().all() and (values.iloc[:-1] > 0).all() else np.nan
    out["salesTrend4Q"] = groups["sales"].transform(lambda s: s.rolling(4).apply(trend, raw=False))
    out["salesVolatility4Q"] = groups["sales"].transform(lambda s: s.rolling(4).apply(volatility, raw=False))
    return out


def aggregate_categories(frame: pd.DataFrame) -> pd.DataFrame:
    keys = ["quarter", "areaId", "areaName", "topCategory"]
    sums = ["sales", "salesCount", "storeCount", "normalStoreCount", "franchiseCount", "openCount", "closeCount"]
    work = frame.copy()
    work["openWeighted"] = work["openRate"] * work["storeCount"]
    work["closeWeighted"] = work["closeRate"] * work["storeCount"]
    result = work.groupby(keys, dropna=False).agg(**{c: (c, "sum") for c in sums}, floatingPopulation=("floatingPopulation", "first"), openWeighted=("openWeighted", "sum"), closeWeighted=("closeWeighted", "sum")).reset_index()
    result["openRate"] = safe_ratio(result.pop("openWeighted"), result["storeCount"])
    result["closeRate"] = safe_ratio(result.pop("closeWeighted"), result["storeCount"])
    result["analysisKey"] = "CAT:" + result["topCategory"].astype(str)
    result["industryCode"] = None
    result["subCategory"] = "전체 " + result["topCategory"].astype(str)
    return result


def percentile_score(series: pd.Series, minimum: int = 8) -> pd.Series:
    result = pd.Series(np.nan, index=series.index, dtype=float)
    valid = series.dropna()
    if len(valid) < minimum:
        return result
    lower, upper = valid.quantile([0.05, 0.95])
    clipped = valid.clip(lower, upper)
    result.loc[valid.index] = clipped.rank(method="average", pct=True).mul(100)
    return result


def add_scores(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    specifications = {"salesGrowthScore": "salesYoY", "populationGrowthScore": "populationYoY", "salesPerStoreGrowthScore": "salesPerStoreYoY", "storeRiskScore": "storeYoY", "salesPerStoreRiskScore": "negativeSalesPerStore", "closeRiskScore": "closeRate", "slowdownRiskScore": "salesSlowdown"}
    out["negativeSalesPerStore"] = -out["salesPerStoreYoY"]
    for score, source in specifications.items():
        out[score] = out.groupby(["quarter", "analysisKey"], group_keys=False)[source].apply(percentile_score)
    health = ["salesGrowthScore", "populationGrowthScore", "salesPerStoreGrowthScore"]
    risk = ["storeRiskScore", "salesPerStoreRiskScore", "closeRiskScore", "slowdownRiskScore"]
    out["currentHealthScore"] = (out[health].notna().all(axis=1) * (out["salesGrowthScore"]*.35 + out["populationGrowthScore"]*.25 + out["salesPerStoreGrowthScore"]*.40)).where(out[health].notna().all(axis=1)).round(1)
    out["riskScore"] = (out["storeRiskScore"]*.30 + out["salesPerStoreRiskScore"]*.35 + out["closeRiskScore"]*.25 + out["slowdownRiskScore"]*.10).where(out[risk].notna().all(axis=1)).round(1)
    out["riskStatus"] = out["riskScore"].apply(risk_status)
    return out.drop(columns=["negativeSalesPerStore"])


def risk_status(value: float | None) -> str | None:
    if value is None or pd.isna(value): return None
    if value < 25: return "safe"
    if value < 50: return "caution"
    if value < 75: return "overheat"
    return "high_risk"


def add_future_target(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.sort_values(["analysisKey", "areaId", "quarter"]).copy()
    groups = out.groupby(["analysisKey", "areaId"], sort=False)
    future = {c: groups[c].shift(-4) for c in ["sales", "floatingPopulation", "salesPerStore"]}
    complete = np.logical_and.reduce([v.notna() for v in future.values()])
    grew = (future["sales"] > out["sales"]) & (future["floatingPopulation"] > out["floatingPopulation"]) & (future["salesPerStore"] > out["salesPerStore"])
    out["futureGrowth"] = pd.Series(np.where(complete, grew.astype(int), np.nan), index=out.index)
    return out


def chronological_split(frame: pd.DataFrame, validation_area_ids: set[str] | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    quarters = sorted(frame.loc[frame["futureGrowth"].notna(), "quarter"].astype(str).unique())
    validation_quarters = set(quarters[-4:])
    train = frame[~frame["quarter"].astype(str).isin(validation_quarters)]
    validation = frame[frame["quarter"].astype(str).isin(validation_quarters)]
    if validation_area_ids is not None:
        validation = validation[validation["areaId"].astype(str).isin(validation_area_ids)]
    return train, validation


def train_models(
    frame: pd.DataFrame,
    training_frame: pd.DataFrame | None = None,
    validation_area_ids: set[str] | None = None,
) -> tuple[pd.DataFrame, list[dict]]:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import balanced_accuracy_score, f1_score, roc_auc_score

    out = frame.copy()
    out["growthScore"] = np.nan
    out["scoreSource"] = "unavailable"
    model_source = training_frame if training_frame is not None else frame
    reports: list[dict] = []

    for key, group in model_source.groupby("analysisKey"):
        labeled = group.dropna(subset=FEATURES + ["futureGrowth"])
        report = {
            "analysisKey": key,
            "labeledRows": len(labeled),
            "trainScope": "seoul" if training_frame is not None else "output",
            "validationScope": "target_district" if validation_area_ids is not None else "all",
            "passed": False,
            "reason": None,
        }
        if len(labeled) < 80:
            report["reason"] = "labeled rows fewer than 80"
            reports.append(report)
            continue

        train, valid = chronological_split(labeled, validation_area_ids)
        report.update({"trainRows": len(train), "validationRows": len(valid)})
        train_counts = train["futureGrowth"].value_counts()
        valid_counts = valid["futureGrowth"].value_counts()
        if (
            train_counts.empty
            or train_counts.min() < 20
            or valid["futureGrowth"].nunique() < 2
            or valid_counts.min() < 10
        ):
            report["reason"] = "class sample threshold not met"
            reports.append(report)
            continue

        model = RandomForestClassifier(
            n_estimators=300,
            random_state=42,
            class_weight="balanced",
            n_jobs=-1,
        ).fit(train[FEATURES], train["futureGrowth"].astype(int))
        probability = model.predict_proba(valid[FEATURES])[:, 1]
        prediction = model.predict(valid[FEATURES])
        metrics = {
            "rocAuc": roc_auc_score(valid["futureGrowth"], probability),
            "balancedAccuracy": balanced_accuracy_score(valid["futureGrowth"], prediction),
            "f1": f1_score(valid["futureGrowth"], prediction),
        }
        report.update({
            "trainQuarters": sorted(train.quarter.unique().tolist()),
            "validationQuarters": sorted(valid.quarter.unique().tolist()),
            "metrics": metrics,
        })

        if metrics["rocAuc"] >= .60 and metrics["balancedAccuracy"] >= .55:
            output_group = out[out["analysisKey"] == key]
            latest = output_group[
                output_group["quarter"] == output_group["quarter"].max()
            ].dropna(subset=FEATURES)
            out.loc[latest.index, "growthScore"] = model.predict_proba(latest[FEATURES])[:, 1] * 100
            out.loc[latest.index, "scoreSource"] = "model"
            report["passed"] = True
        else:
            report["reason"] = "validation metric threshold not met"
        reports.append(report)

    out["safetyScore"] = 100 - out["riskScore"]
    model_ok = out["growthScore"].notna() & out["riskScore"].notna()
    fallback_ok = out["currentHealthScore"].notna() & out["riskScore"].notna()
    out["recommendationScore"] = np.where(
        model_ok,
        out["growthScore"] * .70 + out["safetyScore"] * .30,
        np.where(
            fallback_ok,
            out["currentHealthScore"] * .70 + out["safetyScore"] * .30,
            np.nan,
        ),
    )
    out["recommendationMode"] = np.where(
        model_ok,
        "future",
        np.where(fallback_ok, "current_health", "unavailable"),
    )
    return out, reports

def json_value(value):
    if value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value))): return None
    if isinstance(value, np.generic): return value.item()
    return value

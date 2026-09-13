import pandas as pd

from analysis.pipeline import FEATURES, chronological_split, train_models


def model_fixture(area_count: int = 30) -> pd.DataFrame:
    rows = []
    quarters = [f"202{year}{quarter}" for year in range(1, 4) for quarter in range(1, 5)]
    for area in range(area_count):
        for index, quarter in enumerate(quarters):
            target = (area + index) % 2
            row = {
                "quarter": quarter,
                "areaId": str(area),
                "analysisKey": "IND:X",
                "futureGrowth": target,
                "currentHealthScore": 60.0,
                "riskScore": 20.0,
            }
            row.update({feature: float(target) for feature in FEATURES})
            rows.append(row)
    return pd.DataFrame(rows)


def test_validation_is_time_ordered_and_limited_to_target_district():
    frame = model_fixture()
    songpa_ids = {str(area) for area in range(10)}
    train, validation = chronological_split(frame, songpa_ids)
    assert set(train["quarter"]).isdisjoint(set(validation["quarter"]))
    assert set(validation["areaId"]) == songpa_ids
    assert len(validation) == 40


def test_seoul_training_predicts_only_output_district():
    training = model_fixture()
    songpa_ids = {str(area) for area in range(10)}
    output = training[training["areaId"].isin(songpa_ids)].copy()
    scored, reports = train_models(output, training, songpa_ids)
    report = reports[0]
    assert report["trainScope"] == "seoul"
    assert report["validationScope"] == "target_district"
    assert report["labeledRows"] == 360
    assert report["validationRows"] == 40
    assert report["passed"] is True
    latest = scored[scored["quarter"] == scored["quarter"].max()]
    assert len(latest) == 10
    assert latest["growthScore"].notna().all()

from __future__ import annotations
import json
from pathlib import Path
from analysis.pipeline import ROOT, read_csv_sources, validate_frame

def main() -> int:
    reports = {}
    definitions = {
        "sales": (["quarter","areaId","industryCode","sales","salesCount"], ["sales","salesCount"]),
        "stores": (["quarter","areaId","industryCode","storeCount","closeRate"], ["storeCount","closeRate"]),
        "population": (["quarter","areaId","floatingPopulation"], ["floatingPopulation"]),
    }
    for name, (required, numeric) in definitions.items():
        frame = read_csv_sources(ROOT / f"data/raw/{name}", name)
        if frame.empty: reports[name] = {"rows": 0, "errors": ["원본 CSV 없음"]}
        else: reports[name] = validate_frame(frame, required, [k for k in ["quarter","areaId","industryCode"] if k in required], numeric)
    target = ROOT / "data/processed/validation_report.json"; target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(reports, ensure_ascii=False, indent=2))
    return 1 if any(r["errors"] for r in reports.values()) else 0
if __name__ == "__main__": raise SystemExit(main())

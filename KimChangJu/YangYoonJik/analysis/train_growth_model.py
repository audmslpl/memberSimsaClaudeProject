from __future__ import annotations
import json
import pandas as pd
from analysis.pipeline import ROOT, train_models
def main() -> int:
    path=ROOT/'data/processed/dataset.parquet'
    if not path.exists(): print('dataset.parquet 없음'); return 2
    scored,reports=train_models(pd.read_parquet(path)); scored.to_parquet(ROOT/'data/processed/scored.parquet',index=False)
    (ROOT/'data/processed/model_report.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps(reports,ensure_ascii=False,indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())

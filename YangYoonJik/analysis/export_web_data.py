from __future__ import annotations
import json
from datetime import datetime, timezone
import pandas as pd
from analysis.pipeline import ROOT, json_value

def main() -> int:
    public=ROOT/'public/data'; public.mkdir(parents=True,exist_ok=True)
    mapping=pd.read_csv(ROOT/'data/config/category_mapping.csv')
    categories=[]
    for name, group in mapping.groupby('topCategory',sort=False):
        categories.append({'name':name,'analysisKey':f'CAT:{name}','children':[{'name':f'전체 {name}','analysisKey':f'CAT:{name}','industryCode':None}]+[{'name':r.subCategory,'analysisKey':f'IND:{r.industryCode}','industryCode':r.industryCode} for r in group.itertuples()]})
    (public/'categories.json').write_text(json.dumps({'categories':categories},ensure_ascii=False,indent=2),encoding='utf-8')
    path=ROOT/'data/processed/scored.parquet'; records=[]; quarter=None
    if path.exists():
        frame=pd.read_parquet(path); quarter=str(frame.quarter.max()); frame=frame[frame.quarter.astype(str)==quarter]
        fields=['areaId','areaName','dongName','analysisKey','topCategory','subCategory','industryCode','lng','lat','growthScore','scoreSource','currentHealthScore','riskScore','riskStatus','recommendationScore','recommendationMode','salesYoY','populationYoY','salesPerStoreYoY','storeYoY','closeRate','sales','storeCount']
        records=[{k:json_value(row.get(k)) for k in fields} for row in frame.to_dict('records')]
    payload={'quarter':quarter,'generatedAt':datetime.now(timezone.utc).isoformat(),'records':records}
    (public/'commercial.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    if not (public/'areas.geojson').exists(): (public/'areas.geojson').write_text('{"type":"FeatureCollection","features":[]}',encoding='utf-8')
    print(f'{len(records)} records exported'); return 0
if __name__=='__main__': raise SystemExit(main())

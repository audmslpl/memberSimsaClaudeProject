from __future__ import annotations
import pandas as pd
from analysis.pipeline import ROOT, add_derived_metrics, add_future_target, add_scores, aggregate_categories, read_csv_sources
from analysis.export_areas import load_songpa_areas

def main() -> int:
    sales=read_csv_sources(ROOT/'data/raw/sales','sales'); stores=read_csv_sources(ROOT/'data/raw/stores','stores'); population=read_csv_sources(ROOT/'data/raw/population','population')
    if sales.empty or stores.empty or population.empty:
        print('필수 원본 누락: sales, stores, population이 모두 필요합니다.'); return 2
    mapping=pd.read_csv(ROOT/'data/config/category_mapping.csv')
    areas=load_songpa_areas()
    centroids=areas.to_crs(5181).geometry.centroid
    centers=areas[['areaId','areaName','dongName']].copy()
    centers['lng']=centroids.to_crs(4326).x; centers['lat']=centroids.to_crs(4326).y
    sales=sales.merge(mapping,on='industryCode',how='left').merge(centers,on='areaId',how='inner',suffixes=('','Area'))
    leaf=sales.merge(stores,on=['quarter','areaId','industryCode'],how='inner',suffixes=('','Store')).merge(population,on=['quarter','areaId'],how='inner')
    leaf['analysisKey']='IND:'+leaf['industryCode'].astype(str)
    categories=aggregate_categories(leaf); dataset=pd.concat([leaf,categories],ignore_index=True,sort=False)
    dataset=add_scores(add_derived_metrics(dataset)); dataset=add_future_target(dataset)
    ROOT.joinpath('data/processed/dataset.parquet').parent.mkdir(parents=True,exist_ok=True); dataset.to_parquet(ROOT/'data/processed/dataset.parquet',index=False)
    print(f'{len(dataset)} rows written'); return 0

if __name__=='__main__': raise SystemExit(main())

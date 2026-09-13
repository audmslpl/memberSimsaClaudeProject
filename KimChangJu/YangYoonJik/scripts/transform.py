from __future__ import annotations
import json
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
import geopandas as gpd
import pandas as pd
from pyproj import Transformer
from analysis.pipeline import ROOT, add_derived_metrics, add_future_target, aggregate_categories

API_COLUMNS={
 "sales":{"STDR_YYQU_CD":"quarter","TRDAR_CD":"areaId","TRDAR_CD_NM":"areaName","SVC_INDUTY_CD":"industryCode","SVC_INDUTY_CD_NM":"industryName","THSMON_SELNG_AMT":"sales","THSMON_SELNG_CO":"salesCount"},
 "stores":{"STDR_YYQU_CD":"quarter","TRDAR_CD":"areaId","SVC_INDUTY_CD":"industryCode","STOR_CO":"normalStoreCount","SIMILR_INDUTY_STOR_CO":"storeCount","FRC_STOR_CO":"franchiseCount","OPBIZ_RT":"openRate","OPBIZ_STOR_CO":"openCount","CLSBIZ_RT":"closeRate","CLSBIZ_STOR_CO":"closeCount"},
 "population":{"STDR_YYQU_CD":"quarter","TRDAR_CD":"areaId","TOT_FLPOP_CO":"floatingPopulation"}}

def normalize_rows(rows:list[dict],kind:str,numeric:list[str])->pd.DataFrame:
    frame=pd.DataFrame(rows).rename(columns=API_COLUMNS[kind])
    required=list(API_COLUMNS[kind].values())
    missing=sorted(set(required)-set(frame.columns))
    if missing: raise ValueError(f"{kind} 필수 컬럼 누락: {', '.join(missing)}")
    frame=frame[required].copy()
    for key in ("quarter","areaId"):
        if key in frame: frame[key]=frame[key].astype(str)
    if "industryCode" in frame: frame["industryCode"]=frame["industryCode"].astype(str)
    for column in numeric: frame[column]=pd.to_numeric(frame[column],errors="coerce")
    keys=[key for key in ("quarter","areaId","industryCode") if key in frame]
    if frame.duplicated(keys).any(): raise ValueError(f"{kind} 중복 키 발견")
    return frame

def _polygon_lookup(target_district:str)->dict[str,dict]:
    archive_path=ROOT/"data/raw/area/areas.zip"
    if not archive_path.exists(): return {}
    with TemporaryDirectory() as directory:
        target=Path(directory)
        with zipfile.ZipFile(archive_path) as archive:
            for info in archive.infolist():
                suffix=Path(info.filename).suffix.lower()
                if suffix in {".shp",".shx",".dbf",".prj",".cpg"}: (target/f"areas{suffix}").write_bytes(archive.read(info))
        areas=gpd.read_file(target/"areas.shp").rename(columns={"TRDAR_CD":"areaId","SIGNGU_CD_":"districtName"})
    areas=areas[areas.districtName==target_district].to_crs(4326)
    return {str(row.areaId):json.loads(gpd.GeoSeries([row.geometry],crs=4326).to_json())["features"][0]["geometry"] for row in areas.itertuples()}

def transform_areas(rows:list[dict],target_district:str|None)->list[dict]:
    transformer=Transformer.from_crs(5181,4326,always_xy=True); polygons=_polygon_lookup(target_district) if target_district else {}; result=[]
    for row in rows:
        district_name=str(row.get("SIGNGU_CD_NM", ""))
        if target_district and district_name!=target_district: continue
        x=pd.to_numeric(row.get("XCNTS_VALUE"),errors="coerce"); y=pd.to_numeric(row.get("YDNTS_VALUE"),errors="coerce")
        lng,lat=transformer.transform(float(x),float(y)) if pd.notna(x) and pd.notna(y) else (None,None)
        area_id=str(row.get("TRDAR_CD",""))
        if area_id: result.append({"area_id":area_id,"area_name":row.get("TRDAR_CD_NM"),"area_type":row.get("TRDAR_SE_CD_NM"),"district_code":str(row.get("SIGNGU_CD") or ""),"district_name":district_name,"dong_code":str(row.get("ADSTRD_CD") or ""),"dong_name":row.get("ADSTRD_CD_NM"),"latitude":lat,"longitude":lng,"geometry":polygons.get(area_id)})
    if len({row["area_id"] for row in result})!=len(result): raise ValueError("areas 중복 area_id 발견")
    return result

def build_analysis_dataset(sales_rows:list[dict],store_rows:list[dict],population_rows:list[dict],areas:list[dict])->pd.DataFrame:
    sales=normalize_rows(sales_rows,"sales",["sales","salesCount"]); stores=normalize_rows(store_rows,"stores",["normalStoreCount","storeCount","franchiseCount","openRate","openCount","closeRate","closeCount"]); population=normalize_rows(population_rows,"population",["floatingPopulation"])
    area_ids={row["area_id"] for row in areas}; sales=sales[sales.areaId.isin(area_ids)]; stores=stores[stores.areaId.isin(area_ids)]; population=population[population.areaId.isin(area_ids)]
    mapping=pd.read_csv(ROOT/"data/config/category_mapping.csv")
    sales=sales.merge(mapping,on="industryCode",how="inner")
    leaf=sales.merge(stores,on=["quarter","areaId","industryCode"],how="inner").merge(population,on=["quarter","areaId"],how="inner")
    leaf["analysisKey"]="IND:"+leaf.industryCode
    categories=aggregate_categories(leaf)
    dataset=pd.concat([leaf,categories],ignore_index=True,sort=False)
    metadata=pd.DataFrame(areas).rename(columns={"area_id":"areaId","area_name":"areaName","dong_name":"dongName","latitude":"lat","longitude":"lng"})[["areaId","areaName","dongName","lat","lng"]]
    dataset=dataset.drop(columns=[c for c in ("areaName","dongName","lat","lng") if c in dataset]).merge(metadata,on="areaId",how="inner")
    return add_future_target(add_derived_metrics(dataset))

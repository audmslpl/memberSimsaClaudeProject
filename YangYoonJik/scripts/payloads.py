from __future__ import annotations
from datetime import datetime,timezone
import pandas as pd
from scripts.supabase_rest import clean_records

def category_payload(mapping:pd.DataFrame)->list[dict]:
    return [{"industry_code":r.industryCode,"industry_name":r.industryName,"top_category":r.topCategory,"sub_category":r.subCategory,"display_order":i*10,"enabled":r.mappingStatus=="verified"} for i,r in enumerate(mapping.itertuples(),1)]

def stats_payload(frame:pd.DataFrame)->list[dict]:
    columns={"quarter":"quarter","areaId":"area_id","analysisKey":"analysis_key","industryCode":"industry_code","topCategory":"top_category","subCategory":"sub_category","sales":"sales","salesCount":"sales_count","floatingPopulation":"floating_population","storeCount":"store_count","normalStoreCount":"normal_store_count","franchiseCount":"franchise_count","openRate":"open_rate","openCount":"open_count","closeRate":"close_rate","closeCount":"close_count","salesPerStore":"sales_per_store","salesYoY":"sales_yoy","populationYoY":"population_yoy","storeYoY":"store_yoy","salesPerStoreYoY":"sales_per_store_yoy","salesCountYoY":"sales_count_yoy","franchiseRatio":"franchise_ratio","salesTrend4Q":"sales_trend_4q","salesVolatility4Q":"sales_volatility_4q"}
    return clean_records(frame[list(columns)].rename(columns=columns).to_dict("records"))

def analysis_payload(frame:pd.DataFrame,model_version:str)->list[dict]:
    rows=[]
    for r in frame.itertuples():
        valid=getattr(r,"scoreSource","unavailable")=="model"
        rows.append({"quarter":str(r.quarter),"area_id":str(r.areaId),"analysis_key":r.analysisKey,"industry_code":r.industryCode if pd.notna(r.industryCode) else None,"current_health_score":r.currentHealthScore,"growth_score":r.growthScore if valid else None,"risk_score":r.riskScore,"safety_score":r.safetyScore,"recommendation_score":r.recommendationScore,"recommendation_mode":r.recommendationMode,"risk_status":r.riskStatus,"model_valid":valid,"model_version":model_version if valid else None})
    return clean_records(rows)

def model_run_payload(reports:list[dict],model_version:str)->list[dict]:
    now=datetime.now(timezone.utc).isoformat(); rows=[]
    for report in reports:
        metrics=report.get("metrics") or {}; train=report.get("trainQuarters") or []; valid=report.get("validationQuarters") or []
        rows.append({"analysis_key":report["analysisKey"],"model_version":model_version,"trained_at":now,"train_period":f"{min(train)}~{max(train)}" if train else None,"validation_period":f"{min(valid)}~{max(valid)}" if valid else None,"labeled_rows":report["labeledRows"],"balanced_accuracy":metrics.get("balancedAccuracy"),"f1":metrics.get("f1"),"roc_auc":metrics.get("rocAuc"),"valid":report["passed"],"notes":report.get("reason")})
    return clean_records(rows)

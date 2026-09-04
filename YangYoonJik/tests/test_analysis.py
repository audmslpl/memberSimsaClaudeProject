import numpy as np
import pandas as pd
from analysis.pipeline import add_derived_metrics, add_future_target, add_scores, aggregate_categories, chronological_split, percentile_score, safe_ratio, train_models

def test_zero_denominator_is_missing():
    result=safe_ratio(pd.Series([10]),pd.Series([0])); assert result.isna().all()

def fixture(rows=12):
    records=[]
    for area in range(rows):
        for q in range(1,10):
            records.append({'quarter':f'202{1+(q-1)//4}{1+(q-1)%4}','areaId':str(area),'areaName':str(area),'analysisKey':'IND:X','topCategory':'음식점','sales':100+q*(area+1),'salesCount':50+q,'storeCount':2+area,'normalStoreCount':2,'franchiseCount':1,'openCount':1,'closeCount':1,'openRate':.1,'closeRate':.05+area/1000,'floatingPopulation':1000+q*(area+1)})
    return pd.DataFrame(records)

def test_t_minus_four_yoy():
    out=add_derived_metrics(fixture(1)); assert out.iloc[3].salesYoY != out.iloc[3].salesYoY; assert np.isclose(out.iloc[4].salesYoY,out.iloc[4].sales/out.iloc[0].sales-1)

def test_category_aggregates_raw_values_not_scores():
    source=pd.DataFrame([{'quarter':'20251','areaId':'1','areaName':'가','topCategory':'음식점','sales':100,'salesCount':10,'storeCount':1,'normalStoreCount':1,'franchiseCount':0,'openCount':0,'closeCount':1,'openRate':.1,'closeRate':.2,'floatingPopulation':100},{'quarter':'20251','areaId':'1','areaName':'가','topCategory':'음식점','sales':300,'salesCount':30,'storeCount':3,'normalStoreCount':3,'franchiseCount':1,'openCount':1,'closeCount':0,'openRate':.3,'closeRate':.4,'floatingPopulation':100}])
    out=aggregate_categories(source).iloc[0]; assert out.sales==400 and out.storeCount==4 and out.floatingPopulation==100 and np.isclose(out.openRate,.25)

def test_winsorized_percentile_and_minimum():
    assert percentile_score(pd.Series(range(7))).isna().all(); scored=percentile_score(pd.Series([0,1,2,3,4,5,6,100])); assert scored.between(0,100).all()

def test_risk_weight_and_target():
    out=add_scores(add_derived_metrics(fixture())); valid=out.riskScore.dropna(); assert valid.between(0,100).all()
    targeted=add_future_target(out); first=targeted.iloc[0]; assert first.futureGrowth in (0,1)

def test_chronological_split_and_model_fallback():
    out=add_future_target(add_derived_metrics(fixture(2))); train,valid=chronological_split(out); assert set(train.quarter).isdisjoint(set(valid.quarter))
    scored,reports=train_models(out.assign(currentHealthScore=np.nan,riskScore=np.nan)); assert scored.growthScore.isna().all() and reports[0]['passed'] is False

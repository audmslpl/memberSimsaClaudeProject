from __future__ import annotations
import pandas as pd
from analysis.pipeline import train_models
def score_and_train(dataset:pd.DataFrame,training_dataset:pd.DataFrame|None=None,validation_area_ids:set[str]|None=None)->tuple[pd.DataFrame,list[dict]]:
    return train_models(dataset,training_dataset,validation_area_ids)

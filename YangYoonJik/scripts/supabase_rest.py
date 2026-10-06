from __future__ import annotations
import math
from collections.abc import Iterable
import requests

def clean_value(value):
    if value is None: return None
    if type(value).__name__ == "NAType": return None
    if hasattr(value,"item"): value=value.item()
    if isinstance(value,float) and (math.isnan(value) or math.isinf(value)): return None
    if isinstance(value,float) and value.is_integer(): return int(value)
    return value

def clean_records(records:Iterable[dict])->list[dict]: return [{key:clean_value(value) for key,value in row.items()} for row in records]

class SupabaseRestClient:
    def __init__(self,url:str,service_key:str,timeout:float=60,session:requests.Session|None=None):
        self.url=url.rstrip("/"); self.timeout=timeout; self.session=session or requests.Session(); self.headers={"apikey":service_key,"Content-Type":"application/json"};
        if not service_key.startswith("sb_secret_"): self.headers["Authorization"]=f"Bearer {service_key}"
    def validate_credentials(self)->None:
        response=self.session.get(f"{self.url}/rest/v1/industry_categories",params={"select":"industry_code","limit":"1"},headers=self.headers,timeout=self.timeout)
        if not response.ok:
            detail=response.text[:1000].replace(self.headers["apikey"],"[REDACTED]")
            raise RuntimeError(f"Supabase 인증 확인 실패 ({response.status_code}): {detail}")

    def upsert(self,table:str,records:Iterable[dict],on_conflict:str,batch_size:int=500)->int:
        cleaned=clean_records(records); count=0
        for start in range(0,len(cleaned),batch_size):
            batch=cleaned[start:start+batch_size]
            response=self.session.post(f"{self.url}/rest/v1/{table}",params={"on_conflict":on_conflict},headers={**self.headers,"Prefer":"resolution=merge-duplicates,return=minimal"},json=batch,timeout=self.timeout)
            if not response.ok:
                detail=response.text[:1000].replace(self.headers["apikey"],"[REDACTED]")
                raise RuntimeError(f"Supabase {table} upsert 실패 ({response.status_code}): {detail}")
            count+=len(batch)
        return count

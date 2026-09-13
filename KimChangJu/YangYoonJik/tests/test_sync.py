import math
from unittest.mock import Mock
import pandas as pd
import pytest
from scripts.seoul_api import SeoulApiClient,SeoulApiError
from scripts.supabase_rest import SupabaseRestClient,clean_records
from scripts.transform import normalize_rows,transform_areas

class Response:
    def __init__(self,payload,status=200): self.payload=payload; self.status=status
    def raise_for_status(self):
        if self.status>=400: raise RuntimeError(self.status)
    def json(self): return self.payload

def test_api_pagination_stops_at_total(caplog):
    session=Mock(); session.get.side_effect=[Response({'Svc':{'list_total_count':3,'RESULT':{'CODE':'INFO-000'},'row':[{'id':1},{'id':2}]}}),Response({'Svc':{'list_total_count':3,'RESULT':{'CODE':'INFO-000'},'row':[{'id':3}]}})]
    rows=SeoulApiClient('secret',page_size=2,session=session).fetch_all('Svc')
    assert [r['id'] for r in rows]==[1,2,3] and session.get.call_count==2
    assert 'secret' not in caplog.text

def test_api_error_response_is_rejected():
    session=Mock(); session.get.return_value=Response({'RESULT':{'CODE':'ERROR-301','MESSAGE':'KEY ERROR'}})
    with pytest.raises(SeoulApiError): SeoulApiClient('secret',retries=1,session=session).fetch_page('Svc',1,5)

def test_api_uses_official_http_endpoint():
    url=SeoulApiClient('secret')._url('Svc',1,5,())
    assert url.startswith('http://openapi.seoul.go.kr:8088/')

def test_transform_rejects_duplicates():
    rows=[{'STDR_YYQU_CD':'20251','TRDAR_CD':'1','TOT_FLPOP_CO':'10'}]*2
    with pytest.raises(ValueError,match='중복'): normalize_rows(rows,'population',['floatingPopulation'])

def test_nan_and_infinity_are_null_in_payload():
    cleaned=clean_records([{'a':float('nan'),'b':float('inf'),'c':pd.NA,'d':3,'e':23.0}])[0]
    assert cleaned['a'] is None and cleaned['b'] is None and cleaned['c'] is None and cleaned['d']==3 and cleaned['e']==23 and isinstance(cleaned['e'],int)

def test_supabase_upsert_is_idempotent_contract():
    session=Mock(); response=Mock(); response.raise_for_status.return_value=None; session.post.return_value=response
    count=SupabaseRestClient('https://example.supabase.co','service-key',session=session).upsert('quarterly_stats',[{'quarter':'20251','area_id':'1','analysis_key':'IND:X'}],'quarter,area_id,analysis_key')
    assert count==1; assert session.post.call_args.kwargs['params']['on_conflict']=='quarter,area_id,analysis_key'; assert 'resolution=merge-duplicates' in session.post.call_args.kwargs['headers']['Prefer']

def test_new_supabase_secret_is_not_sent_as_bearer():
    client=SupabaseRestClient('https://example.supabase.co','sb_secret_example')
    assert client.headers['apikey']=='sb_secret_example'
    assert 'Authorization' not in client.headers

def test_target_district_filter(monkeypatch):
    monkeypatch.setattr('scripts.transform._polygon_lookup',lambda _: {})
    rows=[{'TRDAR_CD':'1','TRDAR_CD_NM':'가','SIGNGU_CD_NM':'송파구','XCNTS_VALUE':'210000','YDNTS_VALUE':'445000'},{'TRDAR_CD':'2','TRDAR_CD_NM':'나','SIGNGU_CD_NM':'강남구','XCNTS_VALUE':'210000','YDNTS_VALUE':'445000'}]
    result=transform_areas(rows,'송파구'); assert [r['area_id'] for r in result]==['1']

def test_transform_all_districts_when_filter_is_none(monkeypatch):
    monkeypatch.setattr('scripts.transform._polygon_lookup',lambda _: {})
    rows=[{'TRDAR_CD':'1','TRDAR_CD_NM':'가','SIGNGU_CD_NM':'송파구','XCNTS_VALUE':'210000','YDNTS_VALUE':'445000'},{'TRDAR_CD':'2','TRDAR_CD_NM':'나','SIGNGU_CD_NM':'강남구','XCNTS_VALUE':'210000','YDNTS_VALUE':'445000'}]
    result=transform_areas(rows,None)
    assert {row['district_name'] for row in result}=={'송파구','강남구'}

def test_supabase_credentials_are_checked_before_long_sync():
    session=Mock(); response=Mock(); response.ok=False; response.status_code=401; response.text="Invalid API key"; session.get.return_value=response
    client=SupabaseRestClient("https://example.supabase.co","sb_secret_wrong",session=session)
    with pytest.raises(RuntimeError,match="인증 확인 실패"):
        client.validate_credentials()
    assert session.get.call_args.kwargs["params"]=={"select":"industry_code","limit":"1"}

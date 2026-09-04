from scripts.seoul_api import SeoulApiClient
SERVICE="VwsmTrdarFlpopQq"
def fetch(client:SeoulApiClient,quarter:str|None=None,area_ids:set[str]|None=None)->list[dict]:
    predicate=(lambda row: str(row.get('TRDAR_CD','')) in area_ids) if area_ids else None
    return client.fetch_all(SERVICE,*(([quarter] if quarter else [])),row_filter=predicate)

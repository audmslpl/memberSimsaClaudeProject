from scripts.seoul_api import SeoulApiClient
SERVICE="VwsmTrdarStorQq"
def fetch(client:SeoulApiClient,quarter:str|None=None,area_ids:set[str]|None=None,industry_codes:set[str]|None=None)->list[dict]:
    def predicate(row:dict)->bool:
        area_ok=not area_ids or str(row.get("TRDAR_CD","")) in area_ids
        industry_ok=not industry_codes or str(row.get("SVC_INDUTY_CD","")) in industry_codes
        return area_ok and industry_ok
    return client.fetch_all(SERVICE,*(([quarter] if quarter else [])),row_filter=predicate)

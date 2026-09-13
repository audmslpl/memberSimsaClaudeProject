from __future__ import annotations
import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote
import requests

LOGGER = logging.getLogger("seoul-sync")

class SeoulApiError(RuntimeError): pass

class SeoulApiClient:
    def __init__(self, api_key: str, page_size: int = 1000, timeout: float = 30, retries: int = 3, session: requests.Session | None = None):
        self._key=api_key; self.page_size=page_size; self.timeout=timeout; self.retries=retries; self.session=session or requests.Session()

    def _url(self, service: str, start: int, end: int, filters: tuple[str,...]) -> str:
        parts=[quote(self._key,safe=""),"json",quote(service,safe=""),str(start),str(end),*[quote(v,safe="") for v in filters]]
        return "http://openapi.seoul.go.kr:8088/" + "/".join(parts)

    def fetch_page(self, service: str, start: int, end: int, *filters: str) -> tuple[list[dict], int]:
        last_error: Exception | None=None
        for attempt in range(1,self.retries+1):
            try:
                LOGGER.info("서울시 API 요청 service=%s range=%s-%s attempt=%s",service,start,end,attempt)
                response=self.session.get(self._url(service,start,end,tuple(filters)),timeout=self.timeout)
                response.raise_for_status(); payload=response.json()
                root=payload.get(service)
                if not isinstance(root,dict):
                    error=payload.get("RESULT",{}); raise SeoulApiError(f"서울시 API 오류 {error.get('CODE','UNKNOWN')}: {error.get('MESSAGE','응답 형식 오류')}")
                result=root.get("RESULT",{}); code=result.get("CODE")
                if code not in (None,"INFO-000"): raise SeoulApiError(f"서울시 API 오류 {code}: {result.get('MESSAGE','')}")
                return list(root.get("row") or []), int(root.get("list_total_count") or 0)
            except (requests.RequestException,ValueError) as exc:
                last_error=exc
                if attempt==self.retries: break
        raise SeoulApiError(f"서울시 API 요청 실패: {type(last_error).__name__}") from None

    def fetch_all(self, service: str, *filters: str, on_page: Callable[[list[dict]],None] | None=None, row_filter: Callable[[dict],bool] | None=None, workers: int=8) -> list[dict]:
        first,total=self.fetch_page(service,1,self.page_size,*filters)
        select=lambda page: page if row_filter is None else [row for row in page if row_filter(row)]
        if on_page: on_page(first)
        rows=select(first)
        if not first or len(first)<self.page_size: return rows
        ranges=[(start,min(start+self.page_size-1,total)) for start in range(self.page_size+1,total+1,self.page_size)]
        def load(bounds:tuple[int,int])->list[dict]:
            page,_=self.fetch_page(service,bounds[0],bounds[1],*filters)
            if on_page: on_page(page)
            return select(page)
        with ThreadPoolExecutor(max_workers=max(1,workers)) as executor:
            for page in executor.map(load,ranges): rows.extend(page)
        return rows

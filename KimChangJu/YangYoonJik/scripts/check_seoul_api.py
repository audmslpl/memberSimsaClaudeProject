from __future__ import annotations

from dotenv import dotenv_values

from scripts.config import ROOT
from scripts.seoul_api import SeoulApiClient


SERVICES = (
    "TbgisTrdarRelm",
    "VwsmTrdarSelngQq",
    "VwsmTrdarStorQq",
    "VwsmTrdarFlpopQq",
)


def main() -> int:
    key = str(dotenv_values(ROOT / ".env.local").get("SEOUL_OPEN_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("SEOUL_OPEN_API_KEY가 없습니다")

    client = SeoulApiClient(key, page_size=5, timeout=30, retries=2)
    failures = 0
    for service in SERVICES:
        try:
            rows, total = client.fetch_page(service, 1, 5)
            quarters = sorted(
                str(row["STDR_YYQU_CD"])
                for row in rows
                if row.get("STDR_YYQU_CD")
            )
            latest = quarters[-1] if quarters else "-"
            print(f"{service}: 성공, sample={len(rows)}, total={total}, latest={latest}")
        except Exception as exc:
            failures += 1
            print(f"{service}: 실패, {type(exc).__name__}: {exc}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

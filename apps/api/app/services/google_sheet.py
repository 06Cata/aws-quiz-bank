import csv
import io
from urllib.parse import quote

import httpx


def google_sheet_csv_url(sheet_id: str, sheet_name: str) -> str:
    encoded_sheet = quote(sheet_name, safe="")
    return (
        f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq"
        f"?tqx=out:csv&sheet={encoded_sheet}"
    )


async def fetch_sheet_rows(sheet_id: str, sheet_name: str) -> list[dict[str, str]]:
    url = google_sheet_csv_url(sheet_id, sheet_name)

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()

    text = response.text.lstrip("\ufeff")
    reader = csv.DictReader(io.StringIO(text))
    rows: list[dict[str, str]] = []

    for row in reader:
        normalized = {
            (key or "").strip(): (value or "").strip()
            for key, value in row.items()
            if key is not None
        }
        if any(normalized.values()):
            rows.append(normalized)

    return rows

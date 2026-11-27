"""Collect public TrendForce spot averages for the static dashboard."""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "docs" / "data" / "history.json"
TIMEZONE = timezone(timedelta(hours=8))
SOURCES = {
    "DRAM": "https://www.trendforce.cn/price",
    "NAND Flash": "https://www.trendforce.cn/price/flash",
}

# Names match the public spot-price tables. Their order matches the reference dashboard.
PRODUCTS = [
    ("ddr5_16gb", "DDR5 16Gb (2Gx8) 4800/5600", "DRAM"),
    ("ddr5_16gb_ett", "DDR5 16Gb (2Gx8) eTT", "DRAM"),
    ("ddr4_16gb", "DDR4 16Gb (2Gx8) 3200", "DRAM"),
    ("ddr4_16gb_ett", "DDR4 16Gb (2Gx8) eTT", "DRAM"),
    ("ddr4_8gb", "DDR4 8Gb (1Gx8) 3200", "DRAM"),
    ("ddr4_8gb_ett", "DDR4 8Gb (1Gx8) eTT", "DRAM"),
    ("ddr3_4gb", "DDR3 4Gb 512Mx8 1600/1866", "DRAM"),
    ("slc_2gb", "SLC 2Gb 256MBx8", "NAND Flash"),
    ("slc_1gb", "SLC 1Gb 128MBx8", "NAND Flash"),
    ("mlc_64gb", "MLC 64Gb 8GBx8", "NAND Flash"),
    ("mlc_32gb", "MLC 32Gb 4GBx8", "NAND Flash"),
    ("microsd_128gb", "MicroSD 128GB", "NAND Flash"),
    ("microsd_64gb", "MicroSD 64GB", "NAND Flash"),
    ("microsd_32gb", "MicroSD 32GB", "NAND Flash"),
    ("microsd_16gb", "MicroSD 16GB", "NAND Flash"),
]


class TableReader(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self.text: list[str] = []
        self.row: list[str] | None = None
        self.cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self.row = []
        elif tag in {"td", "th"} and self.row is not None:
            self.cell = []

    def handle_data(self, data: str) -> None:
        self.text.append(data)
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self.cell is not None and self.row is not None:
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            if self.row:
                self.rows.append(self.row)
            self.row = None


def normalize(value: str) -> str:
    return re.sub(r"[\s（）()*]", "", value).upper()


def parse_page(html: str, category: str) -> tuple[str, dict[str, float]]:
    reader = TableReader()
    reader.feed(html)
    visible_text = " ".join(reader.text)
    match = re.search(r"更新日期\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})", visible_text)
    if not match:
        raise ValueError(f"{category}: cannot find source update date")
    source_date = datetime.strptime(match.group(1).replace("/", "-"), "%Y-%m-%d").date().isoformat()

    expected = {normalize(name): key for key, name, group in PRODUCTS if group == category}
    prices: dict[str, float] = {}
    for row in reader.rows:
        if len(row) < 6:
            continue
        key = expected.get(normalize(row[0]))
        if key is None:
            continue
        raw = row[5].replace(",", "").replace("$", "").strip()
        try:
            value = float(raw)
        except ValueError as exc:
            raise ValueError(f"{category}: invalid price for {row[0]}: {raw!r}") from exc
        if value <= 0:
            raise ValueError(f"{category}: nonpositive price for {row[0]}")
        prices[key] = value

    missing = sorted(set(expected.values()) - set(prices))
    if missing:
        raise ValueError(f"{category}: missing products: {', '.join(missing)}")
    return source_date, prices


def fetch(url: str) -> str:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Accept-Language": "zh-CN,zh;q=0.9"})
    with urlopen(request, timeout=30) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def update_history(existing: dict, observations: dict[str, tuple[str, dict[str, float]]]) -> dict:
    series = existing.get("series", {})
    for key, name, category in PRODUCTS:
        source_date, prices = observations[category]
        old = series.get(key, {}).get("points", [])
        by_date = {point["date"]: point["value"] for point in old}
        by_date[source_date] = prices[key]
        series[key] = {
            "name": name,
            "category": category,
            "source_url": SOURCES[category],
            "points": [{"date": date, "value": value} for date, value in sorted(by_date.items())],
        }
    return {
        "checked_at": datetime.now(TIMEZONE).isoformat(timespec="seconds"),
        "source_dates": {category: item[0] for category, item in observations.items()},
        "series": series,
    }


def main() -> None:
    observations = {category: parse_page(fetch(url), category) for category, url in SOURCES.items()}
    existing = json.loads(DATA_FILE.read_text(encoding="utf-8")) if DATA_FILE.exists() else {}
    updated = update_history(existing, observations)
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Updated {len(updated['series'])} series: {updated['source_dates']}")


if __name__ == "__main__":
    main()

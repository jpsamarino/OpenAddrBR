"""
Generate benchmark datasets for SGEODatabaseAsyncSingle functions.
Statistical random sampling from database.
"""

import json
import random
import sqlite3
from pathlib import Path

SGEODB_PATH = (
    "D:/projetos/SD-External-Data/Scripts-Scraping/Get-Lat-Long/ibge_cnefe_v2/data/sgeobr.db"
)
BENCHMARKS_DIR = Path(__file__).parent
BENCHMARKS_DIR.mkdir(exist_ok=True)

BATCH_SIZE = 10000


def sample_col(table: str, col: str, where: str = "1=1", limit: int = BATCH_SIZE):
    conn = sqlite3.connect(SGEODB_PATH)
    rows = conn.execute(
        f"SELECT {col} FROM {table} WHERE {where} ORDER BY RANDOM() LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]


def save_json(filename, data):
    path = BENCHMARKS_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    print(f"  {filename}: {len(data):,} items")


def main():
    print("Generating benchmark datasets...\n")

    # 1. get_city_info: [["city_name", "state"], ...]
    print("[1/8] get_city_info")
    raw = sample_col("cities", "city_name || '|' || state_code", limit=BATCH_SIZE)
    save_json("get_city_info.json", [[d.split("|")[0], d.split("|")[1]] for d in raw])

    # 2. is_multi_street_cep: [zip_code, ...]
    print("[2/8] is_multi_street_cep")
    save_json(
        "is_multi_street_cep.json",
        sample_col(
            "address",
            "zip_code",
            "zip_code IN (SELECT zip_code FROM multi_street_ceps)",
            BATCH_SIZE,
        ),
    )

    # 3. fetch_address_by_cep: [zip_code, ...]
    print("[3/8] fetch_address_by_cep")
    save_json(
        "fetch_address_by_cep.json",
        sample_col("address", "zip_code", "zip_code IS NOT NULL AND zip_code != ''", BATCH_SIZE),
    )

    # 4. fetch_address_by_street_id: [street_id, ...]
    print("[4/8] fetch_address_by_street_id")
    save_json(
        "fetch_address_by_street_id.json",
        sample_col("address", "street_id", "street_id IS NOT NULL", BATCH_SIZE),
    )

    # 5. fetch_geo_location: [{"street_id": x, "number": y}, ...]
    print("[5/8] fetch_geo_location")
    conn = sqlite3.connect(SGEODB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT street_id, address_number as number
        FROM geo_locations
        WHERE street_id IS NOT NULL
        ORDER BY RANDOM()
        LIMIT ?
    """,
        (BATCH_SIZE,),
    ).fetchall()
    conn.close()
    save_json(
        "fetch_geo_location.json",
        [{"street_id": r["street_id"], "number": r["number"]} for r in rows],
    )

    # 6. fetch_street_by_query_ids: [[query_id1, query_id2, ...], city_code]
    print("[6/8] fetch_street_by_query_ids")
    conn = sqlite3.connect(SGEODB_PATH)
    conn.row_factory = sqlite3.Row
    # Get ALL cities with street_query, not just 5000
    cities = conn.execute("""
        SELECT DISTINCT city_code FROM street_query
        WHERE city_code IS NOT NULL
    """).fetchall()
    result = []
    city_codes = [r["city_code"] for r in cities]
    random.shuffle(city_codes)

    # Create items by sampling query_ids from random cities
    for cc in city_codes:
        if len(result) >= BATCH_SIZE:
            break
        # Get all query_ids for this city and sample different subsets
        ids = conn.execute(
            "SELECT query_id FROM street_query WHERE city_code = ?", (cc,)
        ).fetchall()
        if not ids:
            continue
        query_ids = [r["query_id"] for r in ids]

        # Create multiple entries from this city with different samples
        # Each entry has 5-25 random query_ids from this city
        for _ in range(min(20, len(query_ids) // 5)):  # Up to 20 entries per city
            if len(result) >= BATCH_SIZE:
                break
            sample_size = random.randint(5, min(25, len(query_ids)))
            sample_qids = random.sample(query_ids, sample_size)
            result.append([sample_qids, cc])

    conn.close()
    save_json("fetch_street_by_query_ids.json", result)

    # 7. fetch_address_by_street_names: [[street1, street2, ...], city_code]
    print("[7/8] fetch_address_by_street_names")
    conn = sqlite3.connect(SGEODB_PATH)
    conn.row_factory = sqlite3.Row
    # Sample streets from many cities to get enough 10k items
    rows = conn.execute("""
        SELECT city_code, street_normalized
        FROM address
        WHERE street_normalized IS NOT NULL AND street_normalized != ''
          AND city_code IS NOT NULL
        ORDER BY RANDOM()
        LIMIT 500000
    """).fetchall()
    conn.close()

    by_city = {}
    for r in rows:
        cc = r["city_code"]
        if cc not in by_city:
            by_city[cc] = []
        by_city[cc].append(r["street_normalized"])

    result = []
    # Shuffle cities for variety, process until we have 10k
    cities = list(by_city.items())
    random.shuffle(cities)
    for cc, streets in cities:
        if len(streets) >= 5:
            n = min(random.randint(5, 20), len(streets))
            result.append([random.sample(streets, n), cc])
            if len(result) >= BATCH_SIZE:
                break
    # If still not enough, create additional entries by reusing cities
    while len(result) < BATCH_SIZE:
        for cc, streets in cities:
            if len(streets) >= 5:
                n = min(random.randint(5, 20), len(streets))
                result.append([random.sample(streets, n), cc])
                if len(result) >= BATCH_SIZE:
                    break
    save_json("fetch_address_by_street_names.json", result)

    # 8. fetch_query_ids: [city_code, ...]
    print("[8/8] fetch_query_ids")
    save_json("fetch_query_ids.json", sample_col("street_query", "city_code", limit=BATCH_SIZE))

    print(f"\n[DONE] All files in {BENCHMARKS_DIR}")


if __name__ == "__main__":
    main()

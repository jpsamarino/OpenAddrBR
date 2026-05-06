"""
Validation script comparing IBGE geocoder results against Google references.

Usage:
    python -m tests.test_google_comparison
"""

import json
import math
import time
from pathlib import Path
from typing import NamedTuple

from openaddrbr.core.models import AddressRequest
from application import IBGEGeocoder

# --- Config ---
DATA_PATH = Path(__file__).parent / "google_ref_lat_long.json"
BATCH_SIZE = 1000  # how many addresses to process before printing progress
INTERNAL_BATCH_SIZE = (
    32  # how many addresses the IBGE geocoder processes per call (max 32)
)
WORST_N = 100  # number of worst matches to export to file
QT_ITEMS = 4000  # max number of items to process (set to None for all)


# --- Helpers ---
class GeoResult(NamedTuple):
    lat: float
    lon: float


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance in meters between two lat/lon points."""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def text_similarity_score(s1: str, s2: str) -> float:
    """Simple normalized similarity based on common tokens."""
    t1 = set(s1.upper().split())
    t2 = set(s2.upper().split())
    if not t1 or not t2:
        return 0.0
    return len(t1 & t2) / len(t1 | t2)


def load_records(path: Path, limit: int | None) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        records = json.load(f)
    if limit is not None:
        records = records[:limit]
    return records


def build_addresses(records: list[dict]) -> list[tuple[int, AddressRequest]]:
    addresses: list[tuple[int, AddressRequest]] = []
    for i, rec in enumerate(records):
        place = rec.get("place") or {}
        addr = AddressRequest(
            street=place.get("street", ""),
            street_number=_parse_number(place.get("street_number")),
            neighborhood=place.get("neighborhood", ""),
            city=place.get("city", ""),
            state=place.get("state", ""),
            zip_code=place.get("zip_code"),
        )
        addresses.append((i, addr))
    return addresses


def run_geocoding(addresses: list[tuple[int, AddressRequest]], coder):
    total = len(addresses)
    results: list[dict] = [{} for _ in range(total)]
    start_time = time.perf_counter()

    for i in range(0, len(addresses), BATCH_SIZE):

        batch_tuple = addresses[i : i + BATCH_SIZE]
        batch_addr = [a for _, a in batch_tuple]
        batch_idx = [idx for idx, _ in batch_tuple]
        chunk_start = time.perf_counter()
        ibge_results = coder.get_geo_info_batch(
            batch_addr, batch_size=INTERNAL_BATCH_SIZE
        )
        chunk_elapsed = time.perf_counter() - chunk_start
        for idx, ibge_res in zip(batch_idx, ibge_results):
            results[idx] = {"ibge": ibge_res}

        chunk_qps = len(batch_addr) / chunk_elapsed if chunk_elapsed > 0 else 0
        print(
            f"  Processed {min(i + BATCH_SIZE, len(addresses))}/{len(addresses)}  |  QPS: {chunk_qps:.1f}"
        )

    elapsed = time.perf_counter() - start_time
    return results, elapsed


def compute_statistics(
    records: list[dict], results: list[dict], elapsed: float
) -> dict:
    has_ibge = 0
    no_ibge = 0
    distances: list[float] = []
    street_sims: list[float] = []
    neighborhood_sims: list[float] = []
    zip_code_sims: list[float] = []

    for rec, res in zip(records, results):
        ibge = res.get("ibge")

        if ibge is None or (ibge.lat == 0.0 and ibge.long == 0.0):
            no_ibge += 1
            continue

        try:
            google_lat = float(rec["latitude"])
            google_lon = float(rec["longitude"])
        except (ValueError, TypeError):
            no_ibge += 1
            continue

        if not google_lat or not google_lon:
            no_ibge += 1
            continue

        has_ibge += 1
        dist = haversine(google_lat, google_lon, ibge.lat, ibge.long)
        distances.append(dist)

        street_sims.append(
            text_similarity_score(
                ibge.street_name or "", rec.get("place", {}).get("street", "")
            )
        )
        neighborhood_sims.append(
            text_similarity_score(
                ibge.neighborhood or "", rec.get("place", {}).get("neighborhood", "")
            )
        )
        zip_code_sims.append(
            text_similarity_score(
                ibge.zip_code or "", rec.get("place", {}).get("zip_code", "")
            )
        )

    total = len(records)
    return {
        "total": total,
        "has_ibge": has_ibge,
        "no_ibge": no_ibge,
        "elapsed": elapsed,
        "qps": total / elapsed if elapsed > 0 else 0,
        "ms_per_query": (elapsed / total * 1000) if total > 0 else 0,
        "distances": distances,
        "street_sims": street_sims,
        "neighborhood_sims": neighborhood_sims,
        "zip_code_sims": zip_code_sims,
    }


def print_report(stats: dict) -> None:
    print("\n" + "=" * 60)
    print("VALIDATION REPORT")
    print("=" * 60)

    total = stats["total"]
    print(f"\nTotal records:    {total}")
    print(
        f"Got IBGE result:  {stats['has_ibge']} ({stats['has_ibge'] / total * 100:.1f}%)"
    )
    print(
        f"No IBGE result:   {stats['no_ibge']} ({stats['no_ibge'] / total * 100:.1f}%)"
    )

    print(f"\n[Performance]")
    print(f"  Total time:     {stats['elapsed']:.2f}s")
    print(f"  QPS:            {stats['qps']:.1f} queries/s")
    print(f"  Per query:      {stats['ms_per_query']:.2f}ms")

    distances = stats["distances"]
    if distances:
        avg_dist = sum(distances) / len(distances)
        median_dist = sorted(distances)[len(distances) // 2]
        max_dist = max(distances)
        within_100m = sum(1 for d in distances if d <= 100)
        within_1km = sum(1 for d in distances if d <= 1000)

        print(f"\n[Distance (m)]")
        print(f"  Mean:   {avg_dist:.1f}")
        print(f"  Median: {median_dist:.1f}")
        print(f"  Max:    {max_dist:.1f}")
        print(
            f"  <=100m:  {within_100m} ({within_100m / stats['has_ibge'] * 100:.1f}%)"
        )
        print(f"  <=1km:   {within_1km} ({within_1km / stats['has_ibge'] * 100:.1f}%)")

    street_sims = stats["street_sims"]
    if street_sims:
        print(f"\n[Text Similarity]")
        print(f"  Street name:       {sum(street_sims) / len(street_sims):.3f}")
        print(
            f"  Neighborhood:      {sum(stats['neighborhood_sims']) / len(stats['neighborhood_sims']):.3f}"
        )
        print(
            f"  Zip code:          {sum(stats['zip_code_sims']) / len(stats['zip_code_sims']):.3f}"
        )


def build_ranked_list(
    records: list[dict],
    results: list[dict],
    street_sims: list[float],
    neighborhood_sims: list[float],
    zip_code_sims: list[float],
) -> list[tuple[int, float, float, float, float]]:
    ranked: list[tuple[int, float, float, float, float]] = []
    for i, rec in enumerate(records):
        ibge = results[i].get("ibge")
        if ibge and (ibge.lat != 0.0 or ibge.long != 0.0):
            try:
                gl = float(rec["latitude"])
                go = float(rec["longitude"])
                if gl and go:
                    dist = haversine(gl, go, ibge.lat, ibge.long)
                    si = (
                        street_sims[len(ranked)]
                        if len(ranked) < len(street_sims)
                        else 0.0
                    )
                    ni = (
                        neighborhood_sims[len(ranked)]
                        if len(ranked) < len(neighborhood_sims)
                        else 0.0
                    )
                    zi = (
                        zip_code_sims[len(ranked)]
                        if len(ranked) < len(zip_code_sims)
                        else 0.0
                    )
                    ranked.append((i, dist, si, ni, zi))
            except Exception:
                pass

    ranked.sort(key=lambda x: x[1], reverse=True)
    return ranked


# --- Main ---
def main():
    records = load_records(DATA_PATH, QT_ITEMS)

    print(f"[INFO] Loaded {len(records)} reference records")

    addresses = build_addresses(records)

    coder = IBGEGeocoder(verbose=False)
    results, elapsed = run_geocoding(addresses, coder)
    coder.close()

    stats = compute_statistics(records, results, elapsed)
    print_report(stats)

    ranked = build_ranked_list(
        records,
        results,
        stats["street_sims"],
        stats["neighborhood_sims"],
        stats["zip_code_sims"],
    )
    worst_n = ranked[:WORST_N]

    # Save worst matches to file
    output_file = DATA_PATH.parent / f"worst_matches_{WORST_N}.json"
    save_worst_matches(worst_n, records, results, output_file)


def save_worst_matches(
    worst_items: list[tuple[int, float, float, float, float]],
    records: list[dict],
    results: list[dict],
    output_path: Path,
) -> None:
    """Save worst matches to a JSON file for later analysis."""
    output = []
    for rank, (orig_idx, dist, s_sim, n_sim, z_sim) in enumerate(worst_items, 1):
        rec = records[orig_idx]
        ibge = results[orig_idx]["ibge"]
        place = rec.get("place", {})
        query_pt = place.get("query_pt", "")

        entry = {
            "rank": rank,
            "distance_m": round(dist, 2),
            "query": {
                "street": place.get("street", ""),
                "number": place.get("street_number", ""),
                "neighborhood": place.get("neighborhood", ""),
                "city": place.get("city", ""),
                "state": place.get("state", ""),
                "zip_code": place.get("zip_code", ""),
                "query_pt": query_pt,
            },
            "google": {
                "answer": rec.get("answer", ""),
                "latitude": rec.get("latitude", ""),
                "longitude": rec.get("longitude", ""),
            },
            "ibge": {
                "address": ibge.address if ibge else None,
                "street_name": ibge.street_name if ibge else None,
                "number": ibge.number if ibge else None,
                "neighborhood": ibge.neighborhood if ibge else None,
                "city": ibge.city if ibge else None,
                "state": ibge.state if ibge else None,
                "zip_code": ibge.zip_code if ibge else None,
                "latitude": ibge.lat if ibge else None,
                "longitude": ibge.long if ibge else None,
            },
            "similarity": {
                "street": round(s_sim, 3),
                "neighborhood": round(n_sim, 3),
                "zip_code": round(z_sim, 3),
            },
        }
        output.append(entry)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)


def _parse_number(val) -> int:
    if val is None:
        return 0
    if isinstance(val, int):
        return val
    s = str(val).strip()
    if s.upper() in ("S/N", "SN", ""):
        return 0
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return 0


if __name__ == "__main__":
    main()

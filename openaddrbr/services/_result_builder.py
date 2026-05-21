"""Result builder — constructs AddressInfo from StreetCluster."""

from openaddrbr.core.models import StreetCluster
from openaddrbr.core.models._models import AddressInfo, CityCore, GeoLocation
from openaddrbr.utils import normalize_text, text_similarity

__all__ = ["_build_result", "_NormalizedAddr"]


class _NormalizedAddr:
    """Normalized address data used in batch processing."""
    __slots__ = ("order", "address", "city_info", "street_norm", "neighborhood_norm", "zip_code", "number")

    def __init__(
        self,
        order: int,
        address,
        city_info,
        street_norm: str,
        neighborhood_norm: str,
        zip_code: str | None,
        number: int,
    ):
        self.order = order
        self.address = address
        self.city_info = city_info
        self.street_norm = street_norm
        self.neighborhood_norm = neighborhood_norm
        self.zip_code = zip_code
        self.number = number


def _find_best_geo_location(db, street_id: int, number: int, limit_numbers: int = 3) -> GeoLocation | None:
    """Find best geo location for street_id and number with parity matching."""
    rows = db.query_geo_locations(street_id, number, limit_numbers)
    if not rows:
        return None

    ref_is_even = number % 2 == 0
    for row in rows:
        addr_num = row.address_number
        if addr_num is None:
            continue
        try:
            addr_int = int(addr_num)
        except (ValueError, TypeError):
            continue
        addr_is_even = addr_int % 2 == 0
        if ref_is_even == addr_is_even:
            return GeoLocation(
                address_id=row.address_id,
                latitude=row.latitude,
                longitude=row.longitude,
                address_number=addr_int,
            )
    # No parity match - return first
    row = rows[0]
    return GeoLocation(
        address_id=row.address_id,
        latitude=row.latitude,
        longitude=row.longitude,
        address_number=int(row.address_number),
    )


def _build_result(
    street_cluster: StreetCluster,
    street: str,
    street_norm: str,
    neighborhood_norm: str,
    cep: str | None,
    number: int,
    city_info: CityCore,
    db,
) -> AddressInfo | None:
    """Build AddressInfo from street_cluster."""
    street_id = street_cluster.street_id
    rows = db.query_full_address_by_street_id(street_id)
    if not rows:
        return None

    cluster_data: dict[str, set] = {"streets": set(), "neighborhoods": set(), "zip_codes": set()}

    for row in rows:
        if row.street_normalized in street_cluster.street_normalized:
            cluster_data["streets"].add((row.street_normalized, row.street_name))
            cluster_data["neighborhoods"].add((row.neighborhood_normalized, row.neighborhood_name))
            if row.zip_code:
                cluster_data["zip_codes"].add((str(row.zip_code).zfill(8), row.id, row.source_type))

    geo_result = _find_best_geo_location(db, street_id, number)
    if geo_result:
        lat = geo_result.latitude
        long = geo_result.longitude
        number_ref = geo_result.address_number
        address_id_ref_lat_long = geo_result.address_id
    else:
        lat, long = 0.0, 0.0
        number_ref = 0
        address_id_ref_lat_long = None

    # Find best matching street
    best_street = (0.0, "")
    for s_norm, s_accents in cluster_data["streets"]:
        if s_accents == street:
            best_street = (1.0, s_accents)
            break
        sim = text_similarity(street_norm, s_norm)
        if sim > best_street[0]:
            best_street = (sim, s_accents)

    # Find best matching neighborhood
    best_neighborhood = (0.0, "")
    for n_norm, n in cluster_data["neighborhoods"]:
        sim = text_similarity(neighborhood_norm, n_norm)
        if sim > best_neighborhood[0]:
            best_neighborhood = (sim, n)

    # Find best matching zip code
    best_zip_code = (0.0, "")
    if cep:
        for z, _, _ in cluster_data["zip_codes"]:
            sim = text_similarity(cep, z)
            if sim > best_zip_code[0]:
                best_zip_code = (sim, z)
    else:
        for z in cluster_data["zip_codes"]:
            if address_id_ref_lat_long and z[1] == address_id_ref_lat_long:
                if best_zip_code[1] == "" or z[2] == "A":
                    best_zip_code = (1.0, z[0])

    number_display = "s/n" if number == 0 else f"{number}"
    addr_full = f"{best_street[1]}, {number_display}, {best_neighborhood[1]}, {city_info.city_name} - {city_info.state_code}, {best_zip_code[1]}"

    return AddressInfo(
        lat=lat,
        long=long,
        street_name=best_street[1],
        neighborhood=best_neighborhood[1],
        city=city_info.city_name,
        state=city_info.state_code,
        number=number,
        ref_number_lat_long=number_ref if number_ref else 0,
        zip_code=best_zip_code[1],
        address=addr_full,
    )
"""Geocoder — main entry point for address geocoding."""

from pathlib import Path
from typing import Optional

from openaddrbr.core._env import get_default_batch_size
from openaddrbr.core.interfaces import GeocoderDB
from openaddrbr.core.models import (
    AddressInfo,
    AddressRequest,
    CityCore,
    CityInfo,
    GeoLocation,
    NeighborhoodInfo,
    NormalizedAddress,
    StreetCluster,
)
from openaddrbr.data import SQLDB
from openaddrbr.services import (
    Encoder,
    get_city_info,
    is_multi_street_cep,
    search_by_cep,
    search_by_embedding,
    search_city_tantivy,
    search_neighborhood_tantivy,
)
from openaddrbr.utils import normalize_text, text_similarity


def _find_best_geo_location(db: GeocoderDB, street_id: int, number: int, limit_numbers: int = 3) -> GeoLocation | None:
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
    db: GeocoderDB,
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

    best_street = (0.0, "")
    for s_norm, s_accents in cluster_data["streets"]:
        if s_accents == street:
            best_street = (1.0, s_accents)
            break
        sim = text_similarity(street_norm, s_norm)
        if sim > best_street[0]:
            best_street = (sim, s_accents)

    best_neighborhood = (0.0, "")
    for n_norm, n in cluster_data["neighborhoods"]:
        sim = text_similarity(neighborhood_norm, n_norm)
        if sim > best_neighborhood[0]:
            best_neighborhood = (sim, n)

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


class Geocoder:
    """Main geocoder class.

    Combines Encoder (for embeddings) and Database (for queries) to geocode addresses.

    Args:
        backend: Encoder backend (pytorch, pytorch-compiled, onnx, onnx-int8, cuda).
                 Defaults to OPENADDRBR_BACKEND env var or "pytorch".
        data_path: Path to data directory. Defaults to OPENADDRBR_DATA_PATH or package default.
        batch_size: Default batch size for encoding. Defaults to OPENADDRBR_BATCH_SIZE or 16.
        encoder: Optional Encoder instance (for testing). If None, creates default.
        db: Optional SQLDB instance (for testing). If None, creates default.
    """

    def __init__(
        self,
        backend: str | None = None,
        data_path: str | Path | None = None,
        batch_size: int | None = None,
        encoder: Encoder | None = None,
        db: SQLDB | None = None,
    ):
        self.encoder = (
            encoder if encoder is not None else Encoder(backend=backend, batch_size=batch_size)
        )
        self.db = db if db is not None else SQLDB(data_path=data_path)
        self.batch_size = batch_size if batch_size is not None else get_default_batch_size()

    def geocode(
        self,
        street: str,
        neighborhood: str,
        city: str,
        state: str,
        zip_code: str | None = None,
        number: int = 0,
    ) -> AddressInfo | None:
        """Geocode an address to lat/long coordinates.

        Args:
            street: Street name (e.g., "Rua das Flores")
            neighborhood: Neighborhood name (e.g., "Centro")
            city: City name (e.g., "São Paulo")
            state: State code (e.g., "SP")
            zip_code: Optional CEP/brazilian postal code
            number: Optional street number

        Returns:
            AddressInfo or None if not found
        """
        city_info = get_city_info(city, state, db=self.db)
        if not city_info:
            return None

        street_norm = normalize_text(street) if street else ""
        neighborhood_norm = normalize_text(neighborhood) if neighborhood else ""

        clean_zip = None
        if zip_code:
            clean_zip = "".join(c for c in str(zip_code) if c.isdigit()).zfill(8)

        # 1. Try CEP search first (if not multi-street)
        street_cluster = None
        if clean_zip and not is_multi_street_cep(clean_zip, db=self.db):
            street_cluster = search_by_cep(clean_zip, street_norm, neighborhood_norm, db=self.db)

        # 2. Fall back to vector search
        if not street_cluster:
            embedding = self.encoder.encode(street_norm)
            if embedding is not None:
                street_cluster = search_by_embedding(
                    city_info.city_code, embedding, street_norm, neighborhood_norm, db=self.db
                )

        if street_cluster:
            return _build_result(
                street_cluster,
                street,
                street_norm,
                neighborhood_norm,
                clean_zip,
                number,
                city_info,
                self.db,
            )

        return None

    def geocode_batch(
        self,
        addresses: list[AddressRequest],
        batch_size: int | None = None,
    ) -> list[AddressInfo | None]:
        """Geocode multiple addresses in batch.

        Args:
            addresses: List of AddressRequest objects
            batch_size: Batch size for encoding. Defaults to self.batch_size.

        Returns:
            List of AddressInfo or None (in same order as input)
        """
        if not addresses:
            return []
        if batch_size is None:
            batch_size = self.batch_size

        # Normalize all addresses
        normalized: list[NormalizedAddress] = []
        for i, addr in enumerate(addresses):
            city_info = get_city_info(addr.city, addr.state, db=self.db)
            if not city_info:
                continue
            normalized.append(
                NormalizedAddress(
                    order=i,
                    address=addr,
                    city_info=city_info,
                    street_norm=normalize_text(addr.street) if addr.street else "",
                    neighborhood_norm=normalize_text(addr.neighborhood)
                    if addr.neighborhood
                    else "",
                    zip_code=(
                        "".join(c for c in str(addr.zip_code) if c.isdigit()).zfill(8)
                        if addr.zip_code
                        else None
                    ),
                    number=addr.street_number or 0,
                )
            )

        # Sort by city+street for batching
        valid = sorted(
            normalized,
            key=lambda n: (n.city_info.city_code, n.street_norm),
        )

        results: list[AddressInfo | None] = [None] * len(addresses)

        for i in range(0, len(valid), batch_size):
            batch = valid[i : i + batch_size]
            embeddings = self.encoder.encode_batch(
                [addr.street_norm for addr in batch], len(batch)
            )  # fix batch size isnt batch function size

            for addr, embedding in zip(batch, embeddings):
                cluster = None

                if addr.zip_code and not is_multi_street_cep(addr.zip_code, db=self.db):
                    cluster = search_by_cep(
                        addr.zip_code, addr.street_norm, addr.neighborhood_norm, db=self.db
                    )

                if not cluster and embedding is not None:
                    cluster = search_by_embedding(
                        addr.city_info.city_code,
                        embedding,
                        addr.street_norm,
                        addr.neighborhood_norm,
                        db=self.db,
                    )

                if cluster:
                    results[addr.order] = _build_result(
                        cluster,
                        addr.address.street or "",
                        addr.street_norm,
                        addr.neighborhood_norm,
                        addr.zip_code,
                        addr.number,
                        addr.city_info,
                        self.db,
                    )

        return results

    def search_city(self, query: str, limit: int = 10) -> list[CityInfo]:
        """Search for cities by name using ngram autocomplete.

        Args:
            query: City name query (partial match supported)
            limit: Maximum number of results

        Returns:
            List of CityInfo objects with coordinates
        """
        return search_city_tantivy(query, limit)

    def search_neighborhood(
        self, query: str, city_code: int, limit: int = 10
    ) -> list[NeighborhoodInfo]:
        """Search for neighborhoods by name using ngram autocomplete.

        Args:
            query: Neighborhood name query (partial match supported)
            city_code: IBGE city code to filter results
            limit: Maximum number of results

        Returns:
            List of NeighborhoodInfo objects with coordinates
        """
        return search_neighborhood_tantivy(query, city_code, limit)
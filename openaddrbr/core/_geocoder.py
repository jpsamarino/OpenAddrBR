"""Geocoder — main entry point for address geocoding."""

from pathlib import Path

from openaddrbr.core.env import get_default_batch_size
from openaddrbr.core.models import (
    AddressInfo,
    AddressRequest,
    NormalizedAddress,
)
from openaddrbr.data import SqlAddressDataStore
from openaddrbr.data._text_search import TextSearchEngine
from openaddrbr.data._vector_search import VectorSearchEngine
from openaddrbr.services import (
    Encoder,
    build_result,
    get_city_info,
    resolve_street_by_cep,
    search_by_embedding,
)
from openaddrbr.utils import normalize_text


class Geocoder:
    """Main geocoder class.

    Combines Encoder (for embeddings) and Database (for queries) to geocode addresses.

    Args:
        backend: Encoder backend (pytorch, pytorch-compiled, onnx, onnx-int8, cuda).
                 Defaults to OPENADDRBR_BACKEND env var or "pytorch".
        data_path: Path to data directory. Defaults to OPENADDRBR_DATA_PATH or package default.
        batch_size: Default batch size for encoding. Defaults to OPENADDRBR_BATCH_SIZE or 16.
        encoder: Optional Encoder instance (for testing). If None, creates default.
        db: Optional SqlAddressDataStore instance (for testing). If None, creates default.
        usearch_index: Optional VectorSearchEngine instance (for testing). If None, creates default.
        text_engine: Optional TextSearchEngine instance (for testing). If None, creates default.
    """

    def __init__(
        self,
        backend: str | None = None,
        data_path: str | Path | None = None,
        batch_size: int | None = None,
        encoder: Encoder | None = None,
        db: SqlAddressDataStore | None = None,
        usearch_index: VectorSearchEngine | None = None,
        text_engine: TextSearchEngine | None = None,
    ):
        self.encoder = (
            encoder if encoder is not None else Encoder(backend=backend, batch_size=batch_size)
        )
        self.db = db if db is not None else SqlAddressDataStore(data_path=data_path)
        self.usearch_index = usearch_index if usearch_index is not None else VectorSearchEngine(data_path=data_path)
        self.text_engine = text_engine or TextSearchEngine(data_path=data_path)
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
        if clean_zip and not self.db.is_multi_street_cep(clean_zip):
            street_cluster = resolve_street_by_cep(clean_zip, street_norm, neighborhood_norm, db=self.db)

        # 2. Fall back to vector search
        if not street_cluster:
            embedding = self.encoder.encode(street_norm)
            if embedding is not None:
                street_cluster = search_by_embedding(
                    city_info.city_code,
                    embedding,
                    street_norm,
                    neighborhood_norm,
                    db=self.db,
                    usearch_index=self.usearch_index,
                )

        if street_cluster:
            return build_result(
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

                if addr.zip_code and not self.db.is_multi_street_cep(addr.zip_code):
                    cluster = resolve_street_by_cep(
                        addr.zip_code, addr.street_norm, addr.neighborhood_norm, db=self.db
                    )

                if not cluster and embedding is not None:
                    cluster = search_by_embedding(
                        addr.city_info.city_code,
                        embedding,
                        addr.street_norm,
                        addr.neighborhood_norm,
                        db=self.db,
                        usearch_index=self.usearch_index,
                    )

                if cluster:
                    results[addr.order] = build_result(
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
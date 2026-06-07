# Geocoder Flow

Sequência de execução do `Geocoder.geocode()` e `Geocoder.geocode_batch()`.

## geocode() - Fluxo Principal

```mermaid
sequenceDiagram
    autonumber
    participant User as "Usuário"
    participant GC as "Geocoder"
    participant DB as "SqlAddressDataStore"
    participant ENC as "Encoder"
    participant VS as "VectorSearchEngine"
    participant RES as "build_result"

    User->>GC: geocode(street, neighborhood, city, state, zip_code?)

    alt Busca por CEP
        GC->>DB: get_city_info(city, state)
        DB-->>GC: CityInfo
        GC->>DB: is_multi_street_cep(zip_code)

        alt CEP único
            GC->>DB: resolve_street_by_cep(zip_code, street_norm, neighborhood)
            DB-->>GC: StreetCluster
        end
    end

    alt Sem resultado do CEP
        GC->>ENC: encode(street_norm)
        ENC-->>GC: embedding[]

        GC->>VS: search_city_streets(city_code, embedding)
        VS-->>GC: street_ids[]

        GC->>DB: query_street_query(street_ids)
        DB-->>GC: street_names[]
    end

    GC->>RES: build_result(street_cluster, ...)
    RES-->>User: AddressInfo(lat, lon, address, ...)
```

## geocode_batch() - Fluxo em Lote

```mermaid
sequenceDiagram
    autonumber
    participant User as "Usuário"
    participant GC as "Geocoder"
    participant ENC as "Encoder"
    participant DB as "SqlAddressDataStore"
    participant VS as "VectorSearchEngine"
    participant RES as "build_result"

    User->>GC: geocode_batch(addresses[], batch_size?)

    loop Para cada batch
        GC->>ENC: encode_batch(street_norms[], batch_size)
        ENC-->>GC: embeddings[]

        par Para cada address
            alt CEP disponível e único
                GC->>DB: resolve_street_by_cep(zip_code, street_norm, neighborhood)
                DB-->>GC: StreetCluster
            else Fallback vector search
                GC->>VS: search_city_streets(city_code, embedding)
                VS-->>GC: street_ids[]

                GC->>DB: query_street_query(street_ids)
                DB-->>GC: street_names[]
            end
        end

        GC->>RES: build_result() para cada cluster encontrado
        RES-->>GC: AddressInfo[]
    end

    GC-->>User: List[AddressInfo | None]
```

## Fluxo de Decisão

```mermaid
flowchart TD
    Start["geocode() called"] --> CityInfo{"get_city_info()"}
    CityInfo -->|Cidade não encontrada| ReturnNone["return None"]
    CityInfo -->|Cidade encontrada| HasZip{"zip_code fornecido?"}

    HasZip -->|Não| VectorSearch["Encode + Vector Search"]
    HasZip -->|Sim| MultiStreet{"is_multi_street_cep()"}

    MultiStreet -->|Sim| VectorSearch
    MultiStreet -->|Não| CepSearch["resolve_street_by_cep()"]
    CepSearch -->|Encontrado| Build["build_result()"]
    CepSearch -->|Não encontrado| VectorSearch

    VectorSearch -->|embedding gerado| VSSearch["search_city_streets()"]
    VectorSearch -->|sem embedding| ReturnNone
    VSSearch -->|results| Build

    Build -->|AddressInfo| End["return AddressInfo"]
    ReturnNone --> End
```

## Componentes Envolvidos

| Componente | Responsabilidade |
|-----------|-------------------|
| `Geocoder` | Orquestra o fluxo de geocodificação |
| `Encoder` | Gera embeddings de texto (PyTorch/ONNX) |
| `SqlAddressDataStore` | Acesso ao banco SQLite de endereços |
| `VectorSearchEngine` | Busca por similaridade (usearch) |
| `build_result` | Monta o AddressInfo final |
| `get_city_info` | Busca info de cidade por nome/estado |
| `resolve_street_by_cep` | Resolve rua a partir do CEP |
| `search_by_embedding` | Busca por embedding vetorial |

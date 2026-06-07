# LocationSuggestions Flow

Sequência de execução do `LocationSuggestions` para autocomplete de cidades e bairros.

## search_cities() - Fluxo

```mermaid
sequenceDiagram
    autonumber
    participant User as "Usuário"
    participant LS as "LocationSuggestions"
    participant TE as "TextSearchEngine"
    participant TI as "Tantivy Index"

    User->>LS: search_cities(query, limit?)

    LS->>LS: normalize_text(query)
    LS->>TE: search_cities(query_normalized, limit)
    TE->>TI: search(query_text, limit)
    TI-->>TE: hits[]
    TE-->>LS: hits[]

    loop Para cada hit
        LS->>TE: get_city(doc_address)
        TE->>TI: searcher.doc(doc_address)
        TI-->>TE: CityInfo
        TE-->>LS: CityInfo
    end

    LS-->>User: List[CityInfo]
```

## search_neighborhoods() - Fluxo

```mermaid
sequenceDiagram
    autonumber
    participant User as "Usuário"
    participant LS as "LocationSuggestions"
    participant TE as "TextSearchEngine"
    participant TI as "Tantivy Index"

    User->>LS: search_neighborhoods(query, city_code, limit?)

    LS->>LS: normalize_text(query)
    LS->>TE: search_neighborhoods(query_normalized, city_code, limit)
    TE->>TI: search(query_text, city_code, limit)
    TI-->>TE: hits[]
    TE-->>LS: hits[]

    loop Para cada hit
        LS->>TE: get_neighborhood(doc_address)
        TE->>TI: searcher.doc(doc_address)
        TI-->>TE: NeighborhoodInfo
        TE-->>LS: NeighborhoodInfo
    end

    LS-->>User: List[NeighborhoodInfo]
```

## Arquitetura de Busca Textual

```mermaid
flowchart LR
    subgraph "TextSearchEngine"
        A["search_cities() / search_neighborhoods()"]
        B["normalize_text()"]
        C["Tantivy Query"]
        D["searcher.doc() - Read from Tantivy Index"]
    end

    A --> B --> C --> D --> A
```

## Comparação: Geocoder vs LocationSuggestions

| Aspecto | Geocoder | LocationSuggestions |
|---------|----------|---------------------|
| **Propósito** | Geocodificar endereços para lat/lon | Autocomplete de cidades/bairros |
| **Entrada** | Endereço completo | Nome parcial |
| **Busca** | Vector search (usearch) | Text search (Tantivy) |
| **Dados** | SQLite + embeddings | Tantivy index (100%) |
| **Saída** | AddressInfo (lat, lon) | CityInfo / NeighborhoodInfo |

## Componentes Envolvidos

| Componente | Responsabilidade |
|-----------|------------------|
| `LocationSuggestions` | Orquestra busca de cidades/bairros |
| `TextSearchEngine` | Abstração sobre Tantivy index |
| `Tantivy Index` | Índice invertido para busca text |
| `normalize_text` | Normaliza texto para busca |

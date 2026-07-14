import json
import sqlite3
import statistics
import unicodedata
from collections import defaultdict

import msgpack


def tokenize_and_assign_positions(text):
    if not text:
        return []
    tokens = text.split()
    length = len(tokens)
    if length == 0:
        return []

    if length == 1:
        return [(tokens[0], "single", 1)]
    elif length == 2:
        return [(tokens[0], "start", 2), (tokens[1], "end", 2)]
    else:
        results = [(tokens[0], "start", length)]
        for i in range(1, length - 1):
            results.append((tokens[i], "middle", length))
        results.append((tokens[-1], "end", length))
        return results


def is_valid_address(street):
    if not street:
        return False
    street_upper = street.upper()
    if street_upper in ("SEM DENOMINACAO", "PROJETADA", "AREA RURAL"):
        return False
    if street_upper.startswith("BAIRRO "):
        return False
    # if street_upper.startswith("ZONA RURAL DE ") or street_upper.startswith("DISTRITO DE "):
    #     return False
    return True


def build_offline_stats(
    db_path, output_json="address_stats.json", output_msgpack="address_stats.msgpack"
):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # State tracking
    city_counts = defaultdict(int)
    seen_neighborhoods = set()
    prev_street_normalized = None

    # Raw stats accumulator: stats[token][role][pos] = {"qt_addresses": 0, "qt_entities": 0, "lengths": []}
    def new_stat():
        return {"qt_addresses": 0, "qt_entities": 0, "lengths": []}

    stats = defaultdict(lambda: defaultdict(lambda: defaultdict(new_stat)))

    print("Iniciando Passo A (Streaming de Endereços)...")

    cursor.execute("""
        SELECT street_normalized, neighborhood_normalized, city_code
        FROM address
        ORDER BY street_normalized
    """)

    for row in cursor:
        street, neighborhood, city_code = row

        # Ignora linhas anômalas (limpeza base)
        if not is_valid_address(street):
            continue

        street_norm = street.strip() if street else ""
        neighborhood_norm = neighborhood.strip() if neighborhood else ""

        if not street_norm:
            continue

        # 1. Acumulação da Cidade
        city_counts[city_code] += 1

        # 2. Cálculo da Rua
        street_tokens = tokenize_and_assign_positions(street_norm)
        is_new_street = street_norm != prev_street_normalized

        for token, pos, length in street_tokens:
            stats_entry = stats[token]["street"][pos]
            stats_entry["qt_addresses"] += 1
            if is_new_street:
                stats_entry["qt_entities"] += 1
                stats_entry["lengths"].append(length)

        if is_new_street:
            prev_street_normalized = street_norm

        # 3. Cálculo do Bairro
        if neighborhood_norm:
            neighborhood_tokens = tokenize_and_assign_positions(neighborhood_norm)
            is_new_neighborhood = neighborhood_norm not in seen_neighborhoods

            for token, pos, length in neighborhood_tokens:
                stats_entry = stats[token]["neighborhood"][pos]
                stats_entry["qt_addresses"] += 1
                if is_new_neighborhood:
                    stats_entry["qt_entities"] += 1
                    stats_entry["lengths"].append(length)

            if is_new_neighborhood:
                seen_neighborhoods.add(neighborhood_norm)

    print(f"Passo A concluído. {len(city_counts)} cidades encontradas. Ruas distintas processadas.")

    print("Iniciando Passo B (Cruzamento Final de Cidades)...")
    cursor.execute("SELECT city_code, city_normalized FROM cities")
    for row in cursor:
        city_code, city = row
        city_norm = city.strip() if city else ""
        if not city_norm:
            continue

        city_tokens = tokenize_and_assign_positions(city_norm)

        # A contagem de endereços para esse código
        addr_count = city_counts.get(city_code, 0)

        # Uma linha de cidade pode não ter nenhum endereço associado na base,
        # mas ainda assim queremos aprender que o nome existe (qt_entities = 1, qt_addresses = 0)

        for token, pos, length in city_tokens:
            stats_entry = stats[token]["city"][pos]
            stats_entry["qt_addresses"] += addr_count
            stats_entry["qt_entities"] += 1
            stats_entry["lengths"].append(length)

    print("Passo B concluído.")

    print("Consolidando estatísticas (Média e Desvio Padrão)...")
    # Agora calculamos mean e std e preparamos a estrutura final
    final_stats = {"tokens": {}}

    for token, roles in stats.items():
        final_stats["tokens"][token] = {}
        for role, positions in roles.items():
            final_stats["tokens"][token][role] = {}
            for pos, data in positions.items():
                lengths = data["lengths"]
                if lengths:
                    mean = sum(lengths) / len(lengths)
                    std = statistics.pstdev(lengths) if len(lengths) > 1 else 0.0
                else:
                    mean = 0.0
                    std = 0.0

                final_stats["tokens"][token][role][pos] = {
                    "qt_entities": data["qt_entities"],
                    "qt_addresses": data["qt_addresses"],
                    "mean": round(mean, 2),
                    "std": round(std, 2),
                }

    conn.close()

    print(f"Gravando arquivo JSON de debug: {output_json}")
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(final_stats, f, indent=2, ensure_ascii=False)

    print(f"Gravando arquivo binário MessagePack: {output_msgpack}")
    with open(output_msgpack, "wb") as f:
        f.write(msgpack.packb(final_stats, use_bin_type=True))

    print("Pipeline Offline finalizado com sucesso!")
    return final_stats

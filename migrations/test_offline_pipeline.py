import sqlite3
import json
import os
from offline_pipeline import build_offline_stats

def run_test():
    print("Configurando banco de teste (Exemplo da Spec)...")
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    
    cursor.execute("CREATE TABLE address (street_normalized TEXT, neighborhood_normalized TEXT, city_code INTEGER)")
    cursor.execute("CREATE TABLE cities (city_code INTEGER, city_normalized TEXT)")
    
    addresses = [
        ("JOSE HORTA COSTA", "ALVORADA", 1),
        ("MARIA SILVA COSTA", "ALVORADA", 1),
        ("RUA DO CENTRO", "CENTRO", 1)
    ]
    cursor.executemany("INSERT INTO address VALUES (?, ?, ?)", addresses)
    
    cities = [
        (1, "COSTA RICA"),
        (2, "CURITIBA")
    ]
    cursor.executemany("INSERT INTO cities VALUES (?, ?)", cities)
    conn.commit()
    
    # Salva o banco em arquivo na pasta data para a função de build ler
    db_file = os.path.join(os.path.dirname(__file__), "test_sgeobr.db")
    file_conn = sqlite3.connect(db_file)
    conn.backup(file_conn)
    file_conn.close()
    conn.close()
    
    print("Executando pipeline offline...")
    output_json = os.path.join(os.path.dirname(__file__), "address_stats.json")
    output_msgpack = os.path.join(os.path.dirname(__file__), "address_stats.msgpack")
    
    final_stats = build_offline_stats(db_file, output_json, output_msgpack)
    
    os.remove(db_file)
    
    print("\n--- Output JSON Gerado (para a palavra 'costa') ---")
    print(json.dumps({"costa": final_stats["tokens"].get("costa")}, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    run_test()

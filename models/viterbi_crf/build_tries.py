import sqlite3
import os
import marisa_trie

def build():
    db_path = os.environ.get("SGEOBR_DB_PATH", "D:/projetos/SD-External-Data/Scripts-Scraping/Get-Lat-Long/ibge_cnefe_v2/data/sgeobr.db")
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"DB not found at {db_path}")

    print("Carregando Ruas e Bairros do SQLite...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT DISTINCT street_normalized FROM address WHERE street_normalized IS NOT NULL AND street_normalized != ''")
    streets = [row[0].strip() for row in cursor.fetchall()]
    
    cursor.execute("SELECT DISTINCT neighborhood_normalized FROM address WHERE neighborhood_normalized IS NOT NULL AND neighborhood_normalized != ''")
    neighs = [row[0].strip() for row in cursor.fetchall()]
    conn.close()
    
    print(f"Total ruas únicas: {len(streets)}")
    print(f"Total bairros únicos: {len(neighs)}")
    
    # Criar Tries
    street_trie = marisa_trie.Trie(streets)
    neigh_trie = marisa_trie.Trie(neighs)
    
    os.makedirs("models/viterbi_crf", exist_ok=True)
    street_trie.save("models/viterbi_crf/streets.trie")
    neigh_trie.save("models/viterbi_crf/neigh.trie")
    
    print("Tries salvas com sucesso em models/viterbi_crf/")

if __name__ == "__main__":
    build()

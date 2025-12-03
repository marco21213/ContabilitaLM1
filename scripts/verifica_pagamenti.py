"""Script per verificare quanti pagamenti ci sono e se sono tutti nella vista"""
import sqlite3
import configparser
import os

config = configparser.ConfigParser()
config.read('config.ini', encoding='utf-8')
db_path = config.get('Autenticazione', 'percorso_database')

if not os.path.isabs(db_path):
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), db_path)

conn = sqlite3.connect(db_path)
cur = conn.cursor()

print("=" * 70)
print("VERIFICA PAGAMENTI")
print("=" * 70)

# Conta pagamenti totali
cur.execute("SELECT COUNT(*) FROM pagamenti")
tot_pagamenti = cur.fetchone()[0]
print(f"\n1. Pagamenti totali nella tabella pagamenti: {tot_pagamenti}")

# Conta associazioni
cur.execute("SELECT COUNT(*) FROM associazioni_pagamenti WHERE tipo_associazione = 'PAGAMENTO'")
tot_associazioni = cur.fetchone()[0]
print(f"2. Associazioni di tipo PAGAMENTO: {tot_associazioni}")

# Conta pagamenti nella vista
cur.execute("SELECT COUNT(*) FROM vista_movimenti WHERE descrizione LIKE 'Pagamento%' OR descrizione LIKE 'Storno%'")
tot_vista = cur.fetchone()[0]
print(f"3. Pagamenti nella vista vista_movimenti: {tot_vista}")

# Esempio pagamenti con associazioni
print("\n4. Esempio pagamenti con associazioni (primi 5):")
cur.execute("""
    SELECT 
        p.id,
        p.data_pagamento,
        p.modalita_pagamento,
        p.tipo_movimento,
        COUNT(ap.id_associazione) as num_associazioni,
        SUM(ap.importo_associato) as totale_associato
    FROM pagamenti p
    LEFT JOIN associazioni_pagamenti ap ON ap.id_pagamento = p.id AND ap.tipo_associazione = 'PAGAMENTO'
    GROUP BY p.id
    ORDER BY p.data_pagamento DESC
    LIMIT 5
""")
for row in cur.fetchall():
    print(f"   ID: {row[0]}, Data: {row[1]}, Modalità: {row[2]}, Tipo: {row[3]}, Associazioni: {row[4]}, Totale: {row[5] or 0:.2f}")

# Verifica pagamenti senza associazioni
cur.execute("""
    SELECT COUNT(*) 
    FROM pagamenti p
    LEFT JOIN associazioni_pagamenti ap ON ap.id_pagamento = p.id AND ap.tipo_associazione = 'PAGAMENTO'
    WHERE ap.id_associazione IS NULL
""")
senza_assoc = cur.fetchone()[0]
print(f"\n5. Pagamenti senza associazioni: {senza_assoc}")

# Verifica documenti con pagamenti
cur.execute("""
    SELECT 
        d.id,
        d.tipo_documento,
        d.numero_documento,
        COUNT(ap.id_associazione) as num_pagamenti
    FROM documenti d
    LEFT JOIN associazioni_pagamenti ap ON ap.id_documento = d.id AND ap.tipo_associazione = 'PAGAMENTO'
    GROUP BY d.id
    HAVING num_pagamenti > 0
    ORDER BY num_pagamenti DESC
    LIMIT 5
""")
print("\n6. Documenti con più pagamenti associati:")
for row in cur.fetchall():
    print(f"   Doc: {row[1]} {row[2]}, Pagamenti: {row[3]}")

conn.close()
print("\n" + "=" * 70)


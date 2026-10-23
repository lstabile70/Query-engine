"""Crea un piccolo database SQLite di prova (demo.db) per provare l'app senza il tuo database.

    python esempio/crea_demo.py
    DATABASE_URL=sqlite:///demo.db ...
"""

import random
import sqlite3
from datetime import date, timedelta

random.seed(42)
conn = sqlite3.connect("demo.db")
conn.executescript("""
DROP TABLE IF EXISTS righe_ordine;
DROP TABLE IF EXISTS ordini;
DROP TABLE IF EXISTS prodotti;
DROP TABLE IF EXISTS clienti;

CREATE TABLE clienti (
    id INTEGER PRIMARY KEY,
    nome TEXT NOT NULL,
    regione TEXT NOT NULL,
    tipo TEXT NOT NULL CHECK (tipo IN ('B', 'P')),  -- B = azienda, P = privato
    creato_il DATE NOT NULL
);
CREATE TABLE prodotti (
    id INTEGER PRIMARY KEY,
    nome TEXT NOT NULL,
    categoria TEXT NOT NULL,
    prezzo_cent INTEGER NOT NULL
);
CREATE TABLE ordini (
    id INTEGER PRIMARY KEY,
    cliente_id INTEGER NOT NULL REFERENCES clienti(id),
    data DATE NOT NULL,
    stato INTEGER NOT NULL  -- 1 bozza, 2 confermato, 3 spedito, 4 consegnato, 5 annullato
);
CREATE TABLE righe_ordine (
    ordine_id INTEGER NOT NULL REFERENCES ordini(id),
    prodotto_id INTEGER NOT NULL REFERENCES prodotti(id),
    quantita INTEGER NOT NULL,
    prezzo_cent INTEGER NOT NULL
);
""")

regioni = ["Lombardia", "Lazio", "Campania", "Veneto", "Piemonte", "Sicilia", "Toscana", "Puglia"]
nomi = ["Rossi", "Bianchi", "Verdi", "Russo", "Ferrari", "Esposito", "Romano", "Colombo", "Ricci", "Marino"]
conn.executemany(
    "INSERT INTO clienti VALUES (?, ?, ?, ?, ?)",
    [
        (i, f"{random.choice(nomi)} {'Srl' if (t := random.choice('BP')) == 'B' else 'Mario'} {i}",
         random.choice(regioni), t, (date(2023, 1, 1) + timedelta(days=random.randint(0, 900))).isoformat())
        for i in range(1, 201)
    ],
)
prodotti = [
    ("Laptop 14", "Informatica", 89900), ("Monitor 27", "Informatica", 24900), ("Mouse", "Informatica", 1990),
    ("Tastiera", "Informatica", 4990), ("Sedia ergonomica", "Arredo", 32900), ("Scrivania", "Arredo", 45900),
    ("Lampada", "Arredo", 3990), ("Cuffie", "Audio", 12900), ("Altoparlante", "Audio", 7990), ("Webcam", "Video", 6990),
]
conn.executemany("INSERT INTO prodotti VALUES (?, ?, ?, ?)", [(i + 1, *p) for i, p in enumerate(prodotti)])

righe = []
for oid in range(1, 3001):
    giorno = (date(2024, 1, 1) + timedelta(days=random.randint(0, 1020))).isoformat()
    stato = random.choices([1, 2, 3, 4, 5], weights=[3, 10, 15, 60, 12])[0]
    conn.execute("INSERT INTO ordini VALUES (?, ?, ?, ?)", (oid, random.randint(1, 200), giorno, stato))
    for pid in random.sample(range(1, 11), random.randint(1, 4)):
        righe.append((oid, pid, random.randint(1, 5), prodotti[pid - 1][2]))
conn.executemany("INSERT INTO righe_ordine VALUES (?, ?, ?, ?)", righe)
conn.commit()
print("Creato demo.db: 200 clienti, 10 prodotti, 3000 ordini")

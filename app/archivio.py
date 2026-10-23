"""L'archivio dell'app (app.db, SQLite): connessioni, progetti e query salvate.

Lo schema ha un numero di versione (PRAGMA user_version) e si aggiorna da solo
all'avvio. Alla prima esecuzione, se esiste il vecchio progetti.db, viene copiato
qui e i suoi progetti vengono assegnati alla connessione del file .env.
"""

import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.engine import make_url

PERCORSO = Path(os.getenv("DATI_PATH", "app.db"))
VECCHIO_PERCORSO = Path(os.getenv("PROGETTI_PATH", "progetti.db"))  # archivio prima delle connessioni multiple
VERSIONE = 3

LOCK = threading.Lock()  # SQLite regge un solo scrittore: le operazioni passano una alla volta


def connetti() -> sqlite3.Connection:
    conn = sqlite3.connect(PERCORSO)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def adesso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def descrivi_url(url: str | None) -> tuple[str | None, str | None]:
    """(dialetto, nome del database) di una stringa di connessione, senza mai esporre la password."""
    if not url:
        return None, None
    try:
        u = make_url(url)
    except Exception:
        return None, None
    database = u.database
    if u.get_backend_name() == "sqlite" and database:
        database = Path(database).name  # di un file SQLite basta il nome, non il percorso
    return u.get_backend_name(), database


_SCHEMA_CONNESSIONI = """
CREATE TABLE IF NOT EXISTS connessioni (
    id INTEGER PRIMARY KEY,
    nome TEXT NOT NULL UNIQUE COLLATE NOCASE,
    origine TEXT NOT NULL CHECK (origine IN ('env', 'interfaccia')),
    dialetto TEXT,                -- postgresql, mysql, sqlite, mssql, ...
    database TEXT,                -- solo per mostrarlo: la stringa vera non è mai qui in chiaro
    url_cifrata TEXT,             -- NULL per la connessione del .env, che legge DATABASE_URL all'avvio
    parametri TEXT,               -- JSON senza password: serve a ripresentare il modulo di modifica
    solo_metadati INTEGER NOT NULL DEFAULT 0,
    timeout_secondi INTEGER NOT NULL DEFAULT 15,
    creata TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS una_connessione_env ON connessioni(origine) WHERE origine = 'env';
"""

_SCHEMA_PROGETTI = """
CREATE TABLE IF NOT EXISTS progetti (
    id INTEGER PRIMARY KEY,
    connessione_id INTEGER NOT NULL REFERENCES connessioni(id) ON DELETE CASCADE,
    nome TEXT NOT NULL COLLATE NOCASE,
    creato TEXT NOT NULL,
    UNIQUE (connessione_id, nome)
);
CREATE TABLE IF NOT EXISTS query (
    id INTEGER PRIMARY KEY,
    progetto_id INTEGER NOT NULL REFERENCES progetti(id) ON DELETE CASCADE,
    titolo TEXT NOT NULL,
    domanda TEXT NOT NULL,
    sql TEXT NOT NULL,
    spiegazione TEXT NOT NULL,
    dialetto TEXT NOT NULL,
    database TEXT,
    modello TEXT,
    creata TEXT NOT NULL,         -- UTC, ISO 8601
    modificata TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS query_progetto ON query(progetto_id);
"""


def _connessione_env(conn) -> int | None:
    """Id della connessione del .env, creandola se manca e DATABASE_URL è impostata."""
    riga = conn.execute("SELECT id FROM connessioni WHERE origine = 'env'").fetchone()
    if riga:
        return riga["id"]
    url = os.getenv("DATABASE_URL")
    if not url:
        return None
    dialetto, database = descrivi_url(url)
    nome = database or "Predefinita"
    if conn.execute("SELECT 1 FROM connessioni WHERE nome = ?", (nome,)).fetchone():
        nome = f"{nome} (.env)"
    cur = conn.execute(
        "INSERT INTO connessioni (nome, origine, dialetto, database, creata) VALUES (?, 'env', ?, ?, ?)",
        (nome, dialetto, database, adesso()),
    )
    return cur.lastrowid


def _migra_progetti_senza_connessione(conn) -> None:
    """Archivio di prima (progetti senza connessione): i progetti passano alla connessione del .env."""
    colonne = {r["name"] for r in conn.execute("PRAGMA table_info(progetti)")}
    if not colonne or "connessione_id" in colonne:
        return
    env = _connessione_env(conn)
    if env is None:
        raise RuntimeError("Per migrare i progetti esistenti serve DATABASE_URL: vengono assegnati a quella connessione.")
    # Procedura standard di SQLite per cambiare una tabella: nuova tabella, copia, scambio dei nomi
    conn.commit()
    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        with conn:
            conn.execute(
                """CREATE TABLE progetti_nuovi (
                       id INTEGER PRIMARY KEY,
                       connessione_id INTEGER NOT NULL REFERENCES connessioni(id) ON DELETE CASCADE,
                       nome TEXT NOT NULL COLLATE NOCASE,
                       creato TEXT NOT NULL,
                       UNIQUE (connessione_id, nome))"""
            )
            conn.execute("INSERT INTO progetti_nuovi (id, connessione_id, nome, creato)"
                         " SELECT id, ?, nome, creato FROM progetti", (env,))
            conn.execute("DROP TABLE progetti")
            conn.execute("ALTER TABLE progetti_nuovi RENAME TO progetti")
            if conn.execute("PRAGMA foreign_key_check").fetchone():
                raise RuntimeError("Migrazione dei progetti non riuscita: riferimenti non validi")
    finally:
        conn.execute("PRAGMA foreign_keys = ON")


def prepara() -> None:
    """Crea o aggiorna l'archivio. Si chiama una volta all'avvio."""
    with LOCK:
        if not PERCORSO.exists() and VECCHIO_PERCORSO.is_file():
            # Copia "a caldo" con l'API di backup di SQLite: il vecchio file resta com'è
            with sqlite3.connect(VECCHIO_PERCORSO) as vecchio, sqlite3.connect(PERCORSO) as nuovo:
                vecchio.backup(nuovo)
        conn = connetti()
        try:
            versione = conn.execute("PRAGMA user_version").fetchone()[0]
            if versione < 2:
                conn.executescript(_SCHEMA_CONNESSIONI)
                _migra_progetti_senza_connessione(conn)
                conn.executescript(_SCHEMA_PROGETTI)
            if versione < 3:
                # Versione 3: parametri non segreti delle connessioni create dall'interfaccia
                if "parametri" not in {r["name"] for r in conn.execute("PRAGMA table_info(connessioni)")}:
                    conn.execute("ALTER TABLE connessioni ADD COLUMN parametri TEXT")
            if versione < VERSIONE:
                conn.execute(f"PRAGMA user_version = {VERSIONE}")
                conn.commit()
            with conn:
                _connessione_env(conn)
        finally:
            conn.close()

"""Le connessioni ai database: elenco, gestione e stringa di connessione.

La connessione del file .env ("origine env") prende la stringa da DATABASE_URL
e le opzioni da SOLO_METADATI e TIMEOUT_SECONDI, lette all'avvio: nell'archivio
non c'è nessuna sua credenziale e dall'interfaccia non si modifica.

Quelle create dall'interfaccia salvano la stringa cifrata (cifratura.py) e, a
parte, i parametri senza password che servono a ripresentare il modulo.
"""

import json
import os
import sqlite3
from contextlib import closing

from sqlalchemy.engine import URL, make_url

from . import archivio, cifratura


def _vero(valore: str | None) -> bool:
    return (valore or "").lower() in ("1", "true", "si", "sì")


URL_ENV = os.getenv("DATABASE_URL") or None
# Se attivo, le query di Claude possono leggere solo i cataloghi di sistema (struttura
# del DB), mai i dati delle tabelle: nessun dato aziendale arriva ad Anthropic.
SOLO_METADATI_ENV = _vero(os.getenv("SOLO_METADATI"))
TIMEOUT_ENV = int(os.getenv("TIMEOUT_SECONDI", "15"))
MAX_NOME = 120

# Tipi di database proposti nel modulo: driver SQLAlchemy e porta predefinita
TIPI = {
    "mssql": {"nome": "SQL Server", "driver": "mssql+pyodbc", "porta": 1433},
    "postgresql": {"nome": "PostgreSQL", "driver": "postgresql+psycopg", "porta": 5432},
    "mysql": {"nome": "MySQL / MariaDB", "driver": "mysql+pymysql", "porta": 3306},
    "sqlite": {"nome": "SQLite (file)", "driver": "sqlite", "porta": None},
}
MASCHERA = "***"  # come SQLAlchemy nasconde la password: in una stringa modificata significa "non cambiarla"


class NonTrovata(LookupError):
    pass


class NonConfigurata(RuntimeError):
    pass


class NonValida(ValueError):
    pass


def _da_riga(r) -> dict:
    c = {
        "id": r["id"], "nome": r["nome"], "origine": r["origine"], "dialetto": r["dialetto"],
        "database": r["database"], "solo_metadati": bool(r["solo_metadati"]),
        "timeout_secondi": r["timeout_secondi"], "configurata": r["url_cifrata"] is not None,
    }
    if r["origine"] == "env":
        c.update(solo_metadati=SOLO_METADATI_ENV, timeout_secondi=TIMEOUT_ENV, configurata=URL_ENV is not None)
    return c


def sincronizza_env() -> None:
    """All'avvio aggiorna dialetto e nome del database della connessione del .env (servono solo da mostrare)."""
    if not URL_ENV:
        return
    dialetto, database = archivio.descrivi_url(URL_ENV)
    with archivio.LOCK, closing(archivio.connetti()) as conn, conn:
        conn.execute("UPDATE connessioni SET dialetto = ?, database = ? WHERE origine = 'env'", (dialetto, database))


def elenco() -> list[dict]:
    """Tutte le connessioni, prima quella del .env e poi in ordine alfabetico, con il numero di progetti e query.
    Mai le credenziali."""
    with archivio.LOCK, closing(archivio.connetti()) as conn:
        righe = conn.execute(
            """SELECT c.*,
                      (SELECT COUNT(*) FROM progetti p WHERE p.connessione_id = c.id) AS progetti,
                      (SELECT COUNT(*) FROM query q JOIN progetti p ON p.id = q.progetto_id
                        WHERE p.connessione_id = c.id) AS query
               FROM connessioni c ORDER BY c.origine = 'env' DESC, c.nome COLLATE NOCASE""").fetchall()
    return [_da_riga(r) | {"progetti": r["progetti"], "query": r["query"]} for r in righe]


def _riga(conn, connessione_id: int):
    r = conn.execute("SELECT * FROM connessioni WHERE id = ?", (connessione_id,)).fetchone()
    if r is None:
        raise NonTrovata("Connessione non trovata")
    return r


def leggi(connessione_id: int) -> dict:
    with archivio.LOCK, closing(archivio.connetti()) as conn:
        return _da_riga(_riga(conn, connessione_id))


def url(connessione: dict) -> str:
    """La stringa di connessione, da usare solo per collegarsi: non va mai mostrata né registrata."""
    if connessione["origine"] == "env":
        if not URL_ENV:
            raise NonConfigurata(f"La connessione «{connessione['nome']}» usa DATABASE_URL, che non è impostata.")
        return URL_ENV
    with archivio.LOCK, closing(archivio.connetti()) as conn:
        token = _riga(conn, connessione["id"])["url_cifrata"]
    if not token:
        raise NonConfigurata(f"La connessione «{connessione['nome']}» non ha una stringa di connessione.")
    try:
        return cifratura.decifra(token)
    except cifratura.ChiaveMancante as e:
        raise NonConfigurata(str(e)) from e


# ---------- Dal modulo alla stringa di connessione ----------

def _password_precedente(connessione_id: int | None) -> str | None:
    if connessione_id is None:
        return None
    c = leggi(connessione_id)
    if c["origine"] == "env" or not c["configurata"]:
        return None
    return make_url(url(c)).password


def costruisci_url(dati: dict, connessione_id: int | None = None) -> tuple[str, dict]:
    """(stringa di connessione, parametri senza password) dai campi del modulo.

    Modificando una connessione, una password lasciata vuoto (o "***" nella stringa) resta quella di prima.
    """
    precedente = _password_precedente(connessione_id)
    if dati.get("modo") == "stringa":
        testo = (dati.get("stringa") or "").strip()
        if not testo:
            raise NonValida("Scrivi la stringa di connessione")
        try:
            u = make_url(testo)
        except Exception as e:
            raise NonValida("La stringa di connessione non è valida") from e
        if u.password == MASCHERA:
            u = u.set(password=precedente)
        stringa = u.render_as_string(hide_password=False)
        return stringa, {"modo": "stringa", "stringa": u.render_as_string(hide_password=True)}

    tipo = dati.get("tipo")
    if tipo not in TIPI:
        raise NonValida("Scegli il tipo di database")
    database = (dati.get("database") or "").strip()
    if not database:
        raise NonValida("Indica il database" if tipo != "sqlite" else "Indica il percorso del file")
    if tipo == "sqlite":
        return URL.create("sqlite", database=database).render_as_string(hide_password=False), \
            {"modo": "campi", "tipo": tipo, "database": database}

    server = (dati.get("server") or "").strip()
    if not server:
        raise NonValida("Indica il server")
    utente = (dati.get("utente") or "").strip() or None
    password = dati.get("password") or precedente
    query = {}
    driver_odbc = None
    if tipo == "mssql":
        driver_odbc = (dati.get("driver") or "").strip() or "ODBC Driver 17 for SQL Server"
        query["driver"] = driver_odbc
        if dati.get("attendibile"):
            query["TrustServerCertificate"] = "yes"
    u = URL.create(TIPI[tipo]["driver"], username=utente, password=password, host=server,
                   port=dati.get("porta") or None, database=database, query=query)
    parametri = {"modo": "campi", "tipo": tipo, "server": server, "porta": dati.get("porta") or None,
                 "database": database, "utente": utente, "driver": driver_odbc,
                 "attendibile": bool(dati.get("attendibile"))}
    return u.render_as_string(hide_password=False), parametri


def _nome(valore: str) -> str:
    valore = (valore or "").strip()
    if not valore:
        raise NonValida("Dai un nome alla connessione")
    if len(valore) > MAX_NOME:
        raise NonValida(f"Il nome può avere al massimo {MAX_NOME} caratteri")
    return valore


def _scrivi(funzione):
    with archivio.LOCK, closing(archivio.connetti()) as conn:
        try:
            with conn:
                return funzione(conn)
        except sqlite3.IntegrityError as e:
            if "UNIQUE" in str(e):
                raise NonValida("Esiste già una connessione con questo nome") from e
            raise


# ---------- Gestione (solo amministratore) ----------

def parametri(connessione_id: int) -> dict:
    """I dati per il modulo di modifica: tutto tranne la password."""
    with archivio.LOCK, closing(archivio.connetti()) as conn:
        r = _riga(conn, connessione_id)
    c = _da_riga(r)
    p = json.loads(r["parametri"]) if r["parametri"] else {}
    return c | {"parametri": p, "password_impostata": c["origine"] != "env" and c["configurata"]}


def crea(dati: dict) -> dict:
    nome = _nome(dati.get("nome"))
    stringa, param = costruisci_url(dati)
    dialetto, database = archivio.descrivi_url(stringa)
    token = cifratura.cifra(stringa)

    def inserisci(conn):
        cur = conn.execute(
            "INSERT INTO connessioni (nome, origine, dialetto, database, url_cifrata, parametri, solo_metadati,"
            " timeout_secondi, creata) VALUES (?, 'interfaccia', ?, ?, ?, ?, ?, ?, ?)",
            (nome, dialetto, database, token, json.dumps(param), int(bool(dati.get("solo_metadati"))),
             dati.get("timeout_secondi") or 15, archivio.adesso()))
        return cur.lastrowid
    return leggi(_scrivi(inserisci))


def modifica(connessione_id: int, dati: dict) -> dict:
    if leggi(connessione_id)["origine"] == "env":
        raise NonValida("Questa connessione è gestita dal file .env: si modifica lì")
    nome = _nome(dati.get("nome"))
    stringa, param = costruisci_url(dati, connessione_id)
    dialetto, database = archivio.descrivi_url(stringa)
    token = cifratura.cifra(stringa)

    def aggiorna(conn):
        conn.execute(
            "UPDATE connessioni SET nome = ?, dialetto = ?, database = ?, url_cifrata = ?, parametri = ?,"
            " solo_metadati = ?, timeout_secondi = ? WHERE id = ?",
            (nome, dialetto, database, token, json.dumps(param), int(bool(dati.get("solo_metadati"))),
             dati.get("timeout_secondi") or 15, connessione_id))
    _scrivi(aggiorna)
    return leggi(connessione_id)


def elimina(connessione_id: int) -> None:
    """Elimina la connessione con tutti i suoi progetti e le loro query."""
    if leggi(connessione_id)["origine"] == "env":
        raise NonValida("Questa connessione è gestita dal file .env: per toglierla togli DATABASE_URL")
    _scrivi(lambda conn: conn.execute("DELETE FROM connessioni WHERE id = ?", (connessione_id,)))

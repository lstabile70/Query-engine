"""Accesso ai database: solo lettura, timeout e limite di righe.

Tutte le query, sia quelle con cui Claude esplora il DB sia quelle eseguite
dall'utente, passano da qui. La protezione principale resta l'utente del
database con i soli permessi di lettura (vedi README): i controlli di questo
file sono una seconda barriera.

C'è un motore SQLAlchemy per ogni connessione, creato alla prima query.
"""

import threading
from decimal import Decimal
from functools import partial

import sqlglot
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool
from sqlglot import exp

from . import connessioni


def _normalizza_url(url: str) -> str:
    # Usa i driver installati (psycopg 3 e PyMySQL) anche con URL "semplici"
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    if url.startswith("mysql://"):
        return "mysql+pymysql://" + url[len("mysql://"):]
    return url


_SCHEMI_DI_SISTEMA = {"information_schema", "pg_catalog", "sys", "mysql", "performance_schema"}
_TABELLE_DI_SISTEMA = {"sqlite_master", "sqlite_schema"}

_NODI_VIETATI = (
    exp.Insert, exp.Update, exp.Delete, exp.Merge, exp.Create, exp.Drop, exp.Alter,
    exp.TruncateTable, exp.Grant, exp.Revoke, exp.Copy, exp.Set, exp.Pragma, exp.Use,
    exp.Transaction, exp.Commit, exp.Rollback, exp.LoadData, exp.Lock, exp.Command, exp.Into,
)


def _sessione_in_sola_lettura(dialetto: str, timeout: int, dbapi_conn, _record):
    """Imposta ogni nuova connessione in sola lettura e con un timeout."""
    if dialetto == "mssql":
        # SQL Server non ha una sessione in sola lettura: resta l'utente con i soli permessi di lettura.
        # Il timeout delle query è un attributo della connessione pyodbc, in secondi.
        dbapi_conn.timeout = timeout
        return
    comandi = {
        "postgresql": [
            "SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY",
            f"SET statement_timeout = {timeout * 1000}",
        ],
        "mysql": [
            "SET SESSION TRANSACTION READ ONLY",
            f"SET SESSION max_execution_time = {timeout * 1000}",
        ],
        "sqlite": ["PRAGMA query_only = ON"],
    }.get(dialetto, [])
    if not comandi:
        return
    cur = dbapi_conn.cursor()
    for c in comandi:
        cur.execute(c)
    cur.close()
    dbapi_conn.commit()


_motori: dict[int, tuple[str, int, Engine]] = {}  # id connessione → (url, timeout, motore)
_lock_motori = threading.Lock()


def motore(connessione: dict) -> Engine:
    """Il motore della connessione; viene ricreato se nel frattempo stringa o timeout sono cambiati."""
    url = _normalizza_url(connessioni.url(connessione))
    timeout = connessione["timeout_secondi"]
    with _lock_motori:
        attuale = _motori.get(connessione["id"])
        if attuale and attuale[0] == url and attuale[1] == timeout:
            return attuale[2]
        if attuale:
            attuale[2].dispose()
        nuovo = create_engine(url, pool_pre_ping=True)
        event.listen(nuovo, "connect", partial(_sessione_in_sola_lettura, nuovo.dialect.name, timeout))
        _motori[connessione["id"]] = (url, timeout, nuovo)
        return nuovo


def dimentica(connessione_id: int) -> None:
    """Chiude il motore di una connessione modificata o eliminata."""
    with _lock_motori:
        attuale = _motori.pop(connessione_id, None)
    if attuale:
        attuale[2].dispose()


# Per la prova di connessione: versione del server e permessi di scrittura dell'utente (1 = può scrivere)
_VERSIONE = {
    "mssql": "SELECT @@VERSION",
    "postgresql": "SELECT version()",
    "mysql": "SELECT VERSION()",
    "sqlite": "SELECT 'SQLite ' || sqlite_version()",
}
_PUO_SCRIVERE = {
    "mssql": "SELECT CASE WHEN IS_SRVROLEMEMBER('sysadmin') = 1 OR IS_MEMBER('db_owner') = 1"
             " OR IS_MEMBER('db_datawriter') = 1 OR IS_MEMBER('db_ddladmin') = 1 THEN 1 ELSE 0 END",
    "postgresql": "SELECT CASE WHEN (SELECT rolsuper FROM pg_roles WHERE rolname = current_user) OR EXISTS ("
                  "SELECT 1 FROM information_schema.table_privileges WHERE grantee = current_user"
                  " AND privilege_type IN ('INSERT', 'UPDATE', 'DELETE', 'TRUNCATE')) THEN 1 ELSE 0 END",
}


def prova(url: str, timeout: int) -> dict:
    """Prova una stringa di connessione: si collega, legge la versione e controlla i permessi di scrittura.

    Usa un motore temporaneo, chiuso subito dopo. Gli errori arrivano al chiamante.
    """
    url = _normalizza_url(url)
    engine = create_engine(url, poolclass=NullPool)
    dialetto = engine.dialect.name
    event.listen(engine, "connect", partial(_sessione_in_sola_lettura, dialetto, timeout))
    try:
        with engine.connect() as conn:
            versione = conn.exec_driver_sql(_VERSIONE.get(dialetto, "SELECT 1")).scalar()
            scrittura = None  # None = non verificabile per questo database
            if dialetto in _PUO_SCRIVERE:
                scrittura = bool(conn.exec_driver_sql(_PUO_SCRIVERE[dialetto]).scalar())
            elif dialetto == "mysql":
                permessi = " ".join(r[0] for r in conn.exec_driver_sql("SHOW GRANTS"))
                scrittura = any(p in permessi.upper() for p in ("ALL PRIVILEGES", "INSERT", "UPDATE", "DELETE", "DROP"))
            conn.rollback()
    finally:
        engine.dispose()
    return {"dialetto": dialetto, "versione": str(versione).splitlines()[0][:200], "scrittura": scrittura}


class QueryNonPermessa(ValueError):
    pass


def valida(sql: str, dialetto: str, solo_metadati: bool = False) -> str:
    """Accetta una sola SELECT (eventualmente preceduta da EXPLAIN). Restituisce la SQL ripulita."""
    sql = sql.strip().rstrip(";").strip()
    corpo = sql
    if corpo.lower().startswith("explain "):
        corpo = corpo[len("explain "):].lstrip()
        # EXPLAIN ANALYZE esegue davvero la query: non serve e non lo permettiamo
        if corpo.lower().startswith("analyze"):
            raise QueryNonPermessa("EXPLAIN ANALYZE non è permesso")

    dialetto_sqlglot = {"postgresql": "postgres", "mssql": "tsql"}.get(dialetto, dialetto)
    try:
        istruzioni = [s for s in sqlglot.parse(corpo, read=dialetto_sqlglot) if s is not None]
    except sqlglot.errors.ParseError as e:
        raise QueryNonPermessa(f"SQL non valida: {e}") from e

    if len(istruzioni) != 1:
        raise QueryNonPermessa("È permessa una sola istruzione per volta")
    albero = istruzioni[0]
    if not isinstance(albero, exp.Query):
        raise QueryNonPermessa("Sono permesse solo query di lettura (SELECT)")
    vietato = next(albero.find_all(*_NODI_VIETATI), None)
    if vietato is not None:
        raise QueryNonPermessa(f"Operazione non permessa: {vietato.key.upper()}")

    if solo_metadati:
        cte = {c.alias_or_name.lower() for c in albero.find_all(exp.CTE)}
        for t in albero.find_all(exp.Table):
            nome, schema = t.name.lower(), t.db.lower()
            if nome in cte or schema in _SCHEMI_DI_SISTEMA or nome in _TABELLE_DI_SISTEMA:
                continue
            if t.sql().lower().startswith("pragma_"):  # SQLite: pragma_table_info('x'), ...
                continue
            raise QueryNonPermessa(
                f"Modalità solo metadati: puoi leggere solo i cataloghi di sistema, non la tabella {t.sql()}"
            )
    return sql


def esegui(connessione: dict, sql: str, max_righe: int, solo_metadati: bool = False) -> dict:
    """Valida ed esegue una query sulla connessione, restituendo al massimo `max_righe` righe."""
    engine = motore(connessione)
    sql = valida(sql, engine.dialect.name, solo_metadati)
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            # exec_driver_sql passa la query al driver così com'è (niente parametri da interpolare)
            risultato = conn.execution_options(no_parameters=True).exec_driver_sql(sql)
            colonne = list(risultato.keys())
            righe = risultato.fetchmany(max_righe + 1)
        finally:
            trans.rollback()  # non c'è mai niente da salvare
    return {
        "colonne": colonne,
        "righe": [[_serializzabile(v) for v in r] for r in righe[:max_righe]],
        "troncato": len(righe) > max_righe,
    }


def _serializzabile(valore):
    if valore is None or isinstance(valore, (bool, int, float, str)):
        return valore
    if isinstance(valore, Decimal):
        return format(valore.normalize(), "f")  # 6020.0000 → "6020"
    if isinstance(valore, (bytes, bytearray, memoryview)):
        return f"<{len(valore)} byte>"
    return str(valore)  # date, decimal, uuid, ...

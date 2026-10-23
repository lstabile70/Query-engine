"""Progetti e query salvate: il testo SQL con domanda e spiegazione, mai i risultati.

Ogni progetto appartiene a una connessione (database) e le sue query si eseguono
lì. Eliminando un progetto si eliminano anche le sue query. I dati sono
nell'archivio dell'app (archivio.py).
"""

import sqlite3
from contextlib import closing

from . import archivio

MAX_NOME = 120


class NonTrovato(LookupError):
    pass


class NonValido(ValueError):
    pass


def _nome(valore: str, cosa: str) -> str:
    valore = (valore or "").strip()
    if not valore:
        raise NonValido(f"Il {cosa} non può essere vuoto")
    if len(valore) > MAX_NOME:
        raise NonValido(f"Il {cosa} può avere al massimo {MAX_NOME} caratteri")
    return valore


def _esegui(funzione):
    """Apre la connessione, esegue in una transazione e traduce i nomi doppi in un errore leggibile."""
    with archivio.LOCK, closing(archivio.connetti()) as conn:
        try:
            with conn:
                return funzione(conn)
        except sqlite3.IntegrityError as e:
            if "UNIQUE" in str(e):
                raise NonValido("Esiste già un progetto con questo nome per questo database") from e
            raise


def _connessione_esiste(conn, connessione_id: int):
    if conn.execute("SELECT 1 FROM connessioni WHERE id = ?", (connessione_id,)).fetchone() is None:
        raise NonTrovato("Connessione non trovata")


def _progetto(conn, progetto_id: int):
    p = conn.execute("SELECT id, connessione_id FROM progetti WHERE id = ?", (progetto_id,)).fetchone()
    if p is None:
        raise NonTrovato("Progetto non trovato")
    return p


# ---------- Progetti ----------

def elenco(connessione_id: int) -> list[dict]:
    """I progetti della connessione in ordine alfabetico, ciascuno con i titoli delle sue query."""
    def leggi(conn):
        progetti = [dict(p) | {"query": []} for p in conn.execute(
            "SELECT id, nome, creato FROM progetti WHERE connessione_id = ? ORDER BY nome COLLATE NOCASE",
            (connessione_id,))]
        per_id = {p["id"]: p for p in progetti}
        for q in conn.execute(
                "SELECT q.id, q.progetto_id, q.titolo FROM query q JOIN progetti p ON p.id = q.progetto_id"
                " WHERE p.connessione_id = ? ORDER BY q.titolo COLLATE NOCASE", (connessione_id,)):
            per_id[q["progetto_id"]]["query"].append({"id": q["id"], "titolo": q["titolo"]})
        return progetti
    return _esegui(leggi)


def crea_progetto(connessione_id: int, nome: str) -> dict:
    nome = _nome(nome, "nome del progetto")

    def crea(conn):
        _connessione_esiste(conn, connessione_id)
        cur = conn.execute("INSERT INTO progetti (connessione_id, nome, creato) VALUES (?, ?, ?)",
                           (connessione_id, nome, archivio.adesso()))
        return {"id": cur.lastrowid, "nome": nome, "connessione_id": connessione_id}
    return _esegui(crea)


def rinomina_progetto(progetto_id: int, nome: str) -> dict:
    nome = _nome(nome, "nome del progetto")

    def rinomina(conn):
        _progetto(conn, progetto_id)
        conn.execute("UPDATE progetti SET nome = ? WHERE id = ?", (nome, progetto_id))
        return {"id": progetto_id, "nome": nome}
    return _esegui(rinomina)


def elimina_progetto(progetto_id: int) -> None:
    def elimina(conn):
        _progetto(conn, progetto_id)
        conn.execute("DELETE FROM progetti WHERE id = ?", (progetto_id,))
    _esegui(elimina)


# ---------- Query ----------

def salva_query(progetto_id: int, titolo: str, domanda: str, sql: str, spiegazione: str, modello: str | None) -> dict:
    titolo = _nome(titolo, "titolo")
    if not sql.strip():
        raise NonValido("La query è vuota")

    def salva(conn):
        _progetto(conn, progetto_id)
        # Dialetto e database della connessione al momento del salvataggio, come promemoria
        c = conn.execute("SELECT c.dialetto, c.database FROM connessioni c JOIN progetti p ON p.connessione_id = c.id"
                         " WHERE p.id = ?", (progetto_id,)).fetchone()
        ora = archivio.adesso()
        cur = conn.execute(
            "INSERT INTO query (progetto_id, titolo, domanda, sql, spiegazione, dialetto, database, modello,"
            " creata, modificata) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (progetto_id, titolo, domanda, sql, spiegazione, c["dialetto"] or "", c["database"], modello, ora, ora),
        )
        return cur.lastrowid
    return leggi_query(_esegui(salva))


def leggi_query(query_id: int) -> dict:
    def leggi(conn):
        q = conn.execute(
            "SELECT q.*, p.nome AS progetto, p.connessione_id, c.nome AS connessione"
            " FROM query q JOIN progetti p ON p.id = q.progetto_id JOIN connessioni c ON c.id = p.connessione_id"
            " WHERE q.id = ?", (query_id,),
        ).fetchone()
        if q is None:
            raise NonTrovato("Query non trovata")
        return dict(q)
    return _esegui(leggi)


def aggiorna_query(query_id: int, titolo: str | None = None, progetto_id: int | None = None) -> dict:
    """Rinomina la query e/o la sposta in un altro progetto dello stesso database."""
    if titolo is not None:
        titolo = _nome(titolo, "titolo")

    def aggiorna(conn):
        attuale = conn.execute("SELECT p.connessione_id FROM query q JOIN progetti p ON p.id = q.progetto_id"
                               " WHERE q.id = ?", (query_id,)).fetchone()
        if attuale is None:
            raise NonTrovato("Query non trovata")
        if progetto_id is not None and _progetto(conn, progetto_id)["connessione_id"] != attuale["connessione_id"]:
            raise NonValido("Una query si può spostare solo tra progetti dello stesso database")
        conn.execute(
            "UPDATE query SET titolo = COALESCE(?, titolo), progetto_id = COALESCE(?, progetto_id), modificata = ?"
            " WHERE id = ?",
            (titolo, progetto_id, archivio.adesso(), query_id),
        )
    _esegui(aggiorna)
    return leggi_query(query_id)


def elimina_query(query_id: int) -> None:
    def elimina(conn):
        if conn.execute("DELETE FROM query WHERE id = ?", (query_id,)).rowcount == 0:
            raise NonTrovato("Query non trovata")
    _esegui(elimina)

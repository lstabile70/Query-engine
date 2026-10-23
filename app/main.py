"""Server web: la pagina della chat e le API che usa."""

import os
import re
import secrets
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Literal

import anthropic
from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field
from sqlalchemy.engine import make_url

from . import agent, archivio, cifratura, connessioni, consumi, db, impostazioni, progetti

APP_PASSWORD = os.environ.get("APP_PASSWORD", "")
if not APP_PASSWORD:
    raise RuntimeError("Imposta APP_PASSWORD: l'app espone i tuoi database e non può restare aperta a tutti.")
# Seconda password per gestire le connessioni: chi può solo usare l'app non può puntarla su altri database
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
MAX_RIGHE_RISULTATI = int(os.getenv("MAX_RIGHE_RISULTATI", "500"))
MAX_SCAMBI_STORIA = 10

archivio.prepara()  # crea o aggiorna app.db (e alla prima volta vi copia il vecchio progetti.db)
connessioni.sincronizza_env()

app = FastAPI(title="Chat SQL")
_basic = HTTPBasic()


def autenticato(credenziali: HTTPBasicCredentials = Depends(_basic)):
    # Qualsiasi nome utente, la password deve essere APP_PASSWORD
    if not secrets.compare_digest(credenziali.password.encode(), APP_PASSWORD.encode()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, headers={"WWW-Authenticate": "Basic"})


def amministratore(x_password_amministrazione: str | None = Header(None)):
    """Per le operazioni sulle connessioni: oltre ad APP_PASSWORD serve ADMIN_PASSWORD, nell'intestazione
    X-Password-Amministrazione."""
    if not ADMIN_PASSWORD:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Gestione delle connessioni disattivata: imposta ADMIN_PASSWORD.")
    if not secrets.compare_digest((x_password_amministrazione or "").encode(), ADMIN_PASSWORD.encode()):
        time.sleep(1)  # rallenta chi prova le password a raffica
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Password di amministrazione errata.")


class Scambio(BaseModel):
    domanda: str
    risposta: str


class Domanda(BaseModel):
    connessione_id: int
    domanda: str = Field(min_length=1, max_length=4000)
    storia: list[Scambio] = []


class Query(BaseModel):
    connessione_id: int
    sql: str = Field(min_length=1, max_length=50000)


class Impostazioni(BaseModel):
    modello: str
    effort: str


class Progetto(BaseModel):
    nome: str = Field(max_length=progetti.MAX_NOME)


class NuovoProgetto(Progetto):
    connessione_id: int


class QueryDaSalvare(BaseModel):
    progetto_id: int | None = None
    nuovo_progetto: str | None = Field(None, max_length=progetti.MAX_NOME)  # in alternativa a progetto_id
    connessione_id: int | None = None  # serve solo con nuovo_progetto
    titolo: str = Field(max_length=progetti.MAX_NOME)
    domanda: str = Field(max_length=4000)
    sql: str = Field(min_length=1, max_length=50000)
    spiegazione: str = Field("", max_length=10000)
    modello: str | None = None


class DatiConnessione(BaseModel):
    """I campi del modulo della connessione. La password non torna mai indietro dal server."""
    nome: str = Field("", max_length=connessioni.MAX_NOME)
    modo: Literal["campi", "stringa"] = "campi"
    tipo: Literal["mssql", "postgresql", "mysql", "sqlite"] | None = None
    server: str | None = Field(None, max_length=255)
    porta: int | None = Field(None, ge=1, le=65535)
    database: str | None = Field(None, max_length=500)
    utente: str | None = Field(None, max_length=255)
    password: str | None = Field(None, max_length=500)  # vuota modificando = resta quella di prima
    driver: str | None = Field(None, max_length=255)
    attendibile: bool = False  # SQL Server: TrustServerCertificate
    stringa: str | None = Field(None, max_length=2000)
    solo_metadati: bool = False
    timeout_secondi: int = Field(15, ge=1, le=600)


class ProvaConnessione(DatiConnessione):
    connessione_id: int | None = None  # modificando: per riusare la password già salvata


class ModificaQuery(BaseModel):
    titolo: str | None = Field(None, max_length=progetti.MAX_NOME)
    progetto_id: int | None = None


@app.get("/health")
def health():
    return {"ok": True}


def _file_statico(nome: str) -> FileResponse:
    # no-cache: il browser chiede sempre se il file è cambiato, così dopo un aggiornamento non mostra la versione vecchia
    return FileResponse(Path(__file__).parent / "static" / nome, headers={"Cache-Control": "no-cache"})


@app.get("/", dependencies=[Depends(autenticato)])
def pagina():
    return _file_statico("index.html")


@app.get("/consumi", dependencies=[Depends(autenticato)])
def pagina_consumi():
    return _file_statico("consumi.html")


@app.get("/impostazioni", dependencies=[Depends(autenticato)])
def pagina_impostazioni():
    return _file_statico("impostazioni.html")


@app.get("/connessioni", dependencies=[Depends(autenticato)])
def pagina_connessioni():
    return _file_statico("connessioni.html")


@app.get("/query/{query_id}", dependencies=[Depends(autenticato)])
def pagina_query(query_id: int):
    return _file_statico("query.html")  # la pagina legge l'id dall'indirizzo e chiede i dati a /api/query


_RISORSE = {"stile.css", "menu.js", "componenti.js"}  # file comuni alle pagine


@app.get("/static/{nome}", dependencies=[Depends(autenticato)])
def risorsa(nome: str):
    if nome not in _RISORSE:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return _file_statico(nome)


def _connessione(connessione_id: int) -> dict:
    try:
        return connessioni.leggi(connessione_id)
    except connessioni.NonTrovata as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))


@app.get("/api/connessioni", dependencies=[Depends(autenticato)])
def elenco_connessioni():
    """Le connessioni configurate, senza credenziali."""
    return connessioni.elenco()


@app.get("/api/connessioni/stato", dependencies=[Depends(autenticato)])
def stato_connessioni():
    """Se la gestione è attiva, cosa manca per attivarla, i tipi di database e i driver ODBC installati."""
    manca = [nome for nome, presente in (("ADMIN_PASSWORD", ADMIN_PASSWORD), ("CHIAVE_CIFRATURA", cifratura.ATTIVA))
             if not presente]
    try:
        import pyodbc
        # Prima i driver moderni ("ODBC Driver 18", "17", ...), poi quelli vecchi
        driver_odbc = sorted((d for d in pyodbc.drivers() if "SQL Server" in d),
                             key=lambda d: (not d.startswith("ODBC Driver"), [-int(n) for n in re.findall(r"\d+", d)]))
    except ImportError:
        driver_odbc = []
    return {"gestione": not manca, "manca": manca, "driver_odbc": driver_odbc,
            "tipi": [{"id": k, "nome": v["nome"], "porta": v["porta"]} for k, v in connessioni.TIPI.items()]}


@contextmanager
def _errori_connessioni():
    try:
        yield
    except connessioni.NonTrovata as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    except (connessioni.NonValida, connessioni.NonConfigurata, cifratura.ChiaveMancante) as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))


def _messaggio_pulito(errore: Exception, stringa: str) -> str:
    """Il messaggio di errore del driver, senza la password e senza i rimandi alla documentazione di SQLAlchemy."""
    testo = str(getattr(errore, "orig", None) or errore)
    password = make_url(stringa).password
    if password:
        testo = testo.replace(password, connessioni.MASCHERA)
    return re.sub(r"\(Background on this error.*", "", testo).strip()[:600]


@app.post("/api/amministrazione/verifica", dependencies=[Depends(autenticato), Depends(amministratore)])
def verifica_amministratore():
    """La pagina lo chiama per controllare la password di amministrazione prima di aprire la gestione."""
    return {"ok": True}


@app.post("/api/connessioni/prova", dependencies=[Depends(autenticato), Depends(amministratore)])
def prova_connessione(dati: ProvaConnessione):
    """Prova i dati del modulo senza salvarli. Un errore di collegamento non è un errore della richiesta."""
    with _errori_connessioni():
        stringa, _ = connessioni.costruisci_url(dati.model_dump(), dati.connessione_id)
    return _prova(stringa, dati.timeout_secondi)


def _prova(stringa: str, timeout: int) -> dict:
    inizio = time.monotonic()
    try:
        esito = db.prova(stringa, timeout)
    except Exception as e:
        return {"ok": False, "errore": _messaggio_pulito(e, stringa)}
    return {"ok": True, **esito, "millisecondi": round((time.monotonic() - inizio) * 1000)}


@app.post("/api/connessioni/{connessione_id}/prova", dependencies=[Depends(autenticato)])
def prova_connessione_salvata(connessione_id: int):
    """Controlla che un database salvato risponda: per tutti, perché non mostra né cambia niente."""
    c = _connessione(connessione_id)
    with _errori_connessioni():
        stringa = connessioni.url(c)
    return _prova(stringa, c["timeout_secondi"])


@app.get("/api/connessioni/{connessione_id}/parametri", dependencies=[Depends(autenticato), Depends(amministratore)])
def parametri_connessione(connessione_id: int):
    """I campi per il modulo di modifica, senza la password."""
    with _errori_connessioni():
        return connessioni.parametri(connessione_id)


@app.post("/api/connessioni", dependencies=[Depends(autenticato), Depends(amministratore)])
def crea_connessione(dati: DatiConnessione):
    with _errori_connessioni():
        return connessioni.crea(dati.model_dump())


@app.put("/api/connessioni/{connessione_id}", dependencies=[Depends(autenticato), Depends(amministratore)])
def modifica_connessione(connessione_id: int, dati: DatiConnessione):
    with _errori_connessioni():
        c = connessioni.modifica(connessione_id, dati.model_dump())
    db.dimentica(connessione_id)  # il motore si ricrea con i dati nuovi alla prossima query
    return c


@app.delete("/api/connessioni/{connessione_id}", dependencies=[Depends(autenticato), Depends(amministratore)])
def elimina_connessione(connessione_id: int):
    """Elimina la connessione con i suoi progetti e le loro query."""
    with _errori_connessioni():
        connessioni.elimina(connessione_id)
    db.dimentica(connessione_id)
    return {"ok": True}


@app.get("/api/info", dependencies=[Depends(autenticato)])
def info(connessione_id: int):
    """Cosa mostra il menu: database della connessione e modello in uso (mai le credenziali)."""
    c = _connessione(connessione_id)
    scelte = impostazioni.correnti()
    return {
        "connessione": c["nome"],
        "dialetto": c["dialetto"],
        "database": c["database"],
        "configurata": c["configurata"],
        "modello": scelte["modello"],
        "effort": scelte["effort"],
        "solo_metadati": c["solo_metadati"],
    }


def _impostazioni_complete() -> dict:
    """Valori correnti, predefiniti del .env e scelte possibili, con i prezzi per milione di token."""
    modelli = [{**m, "prezzi": dict(zip(("input", "output", "cache_lettura"), consumi.PREZZI[m["id"]]))
                if m["id"] in consumi.PREZZI else None} for m in impostazioni.MODELLI]
    return {
        **impostazioni.correnti(),
        "predefiniti": {"modello": impostazioni.MODELLO_PREDEFINITO, "effort": impostazioni.EFFORT_PREDEFINITO},
        "modelli": modelli,
        "effort_disponibili": impostazioni.EFFORT,
    }


@app.get("/api/impostazioni", dependencies=[Depends(autenticato)])
def leggi_impostazioni():
    return _impostazioni_complete()


@app.put("/api/impostazioni", dependencies=[Depends(autenticato)])
def salva_impostazioni(nuove: Impostazioni):
    """Valgono dalla domanda successiva, senza riavviare il server."""
    try:
        impostazioni.salva(nuove.modello, nuove.effort)
    except impostazioni.ImpostazioneNonValida as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    return _impostazioni_complete()


@app.delete("/api/impostazioni", dependencies=[Depends(autenticato)])
def ripristina_impostazioni():
    """Torna ai valori del file .env."""
    impostazioni.ripristina()
    return _impostazioni_complete()


@app.get("/api/consumi", dependencies=[Depends(autenticato)])
def riepilogo_consumi():
    """Token e costo stimato delle chiamate a Claude. Il saldo vero è nella console di Anthropic."""
    return consumi.riepilogo()


@app.post("/api/chiedi", dependencies=[Depends(autenticato)])
def chiedi(richiesta: Domanda):
    connessione = _connessione(richiesta.connessione_id)
    storia = [s.model_dump() for s in richiesta.storia[-MAX_SCAMBI_STORIA:]]
    try:
        return agent.genera_query(connessione, richiesta.domanda, storia)
    except connessioni.NonConfigurata as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    except agent.ErroreAgente as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e))
    except anthropic.RateLimitError:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Troppe richieste a Claude, riprova tra poco.")
    except anthropic.AuthenticationError:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Chiave API di Anthropic non valida.")
    except anthropic.APIConnectionError:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Impossibile raggiungere l'API di Claude.")
    except anthropic.APIStatusError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Errore dall'API di Claude ({e.status_code}).")


@app.post("/api/esegui", dependencies=[Depends(autenticato)])
def esegui(query: Query):
    """Esegue la query consegnata, quando l'utente lo chiede. I risultati non vengono inviati a Claude."""
    connessione = _connessione(query.connessione_id)
    try:
        return db.esegui(connessione, query.sql, MAX_RIGHE_RISULTATI)
    except (db.QueryNonPermessa, connessioni.NonConfigurata) as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    except Exception as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Errore del database: {e}")


# ---------- Progetti e query salvate (solo il testo SQL, mai i risultati) ----------

@contextmanager
def _errori_progetti():
    try:
        yield
    except progetti.NonTrovato as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    except progetti.NonValido as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))


@app.get("/api/progetti", dependencies=[Depends(autenticato)])
def elenco_progetti(connessione_id: int):
    """I progetti di una connessione, con i titoli delle loro query."""
    return progetti.elenco(connessione_id)


@app.post("/api/progetti", dependencies=[Depends(autenticato)])
def crea_progetto(nuovo: NuovoProgetto):
    with _errori_progetti():
        return progetti.crea_progetto(nuovo.connessione_id, nuovo.nome)


@app.patch("/api/progetti/{progetto_id}", dependencies=[Depends(autenticato)])
def rinomina_progetto(progetto_id: int, modifica: Progetto):
    with _errori_progetti():
        return progetti.rinomina_progetto(progetto_id, modifica.nome)


@app.delete("/api/progetti/{progetto_id}", dependencies=[Depends(autenticato)])
def elimina_progetto(progetto_id: int):
    """Elimina il progetto e tutte le sue query."""
    with _errori_progetti():
        progetti.elimina_progetto(progetto_id)
    return {"ok": True}


@app.post("/api/query", dependencies=[Depends(autenticato)])
def salva_query(q: QueryDaSalvare):
    with _errori_progetti():
        progetto_id = q.progetto_id
        if q.nuovo_progetto:
            if q.connessione_id is None:
                raise progetti.NonValido("Per un nuovo progetto serve la connessione")
            progetto_id = progetti.crea_progetto(q.connessione_id, q.nuovo_progetto)["id"]
        if progetto_id is None:
            raise progetti.NonValido("Scegli un progetto")
        return progetti.salva_query(progetto_id, q.titolo, q.domanda, q.sql, q.spiegazione, q.modello)


@app.get("/api/query/{query_id}", dependencies=[Depends(autenticato)])
def leggi_query(query_id: int):
    with _errori_progetti():
        return progetti.leggi_query(query_id)


@app.patch("/api/query/{query_id}", dependencies=[Depends(autenticato)])
def modifica_query(query_id: int, modifica: ModificaQuery):
    """Rinomina la query e/o la sposta in un altro progetto."""
    with _errori_progetti():
        return progetti.aggiorna_query(query_id, modifica.titolo, modifica.progetto_id)


@app.delete("/api/query/{query_id}", dependencies=[Depends(autenticato)])
def elimina_query(query_id: int):
    with _errori_progetti():
        progetti.elimina_query(query_id)
    return {"ok": True}

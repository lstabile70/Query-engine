"""Il dialogo con Claude: esplora il database con esegui_sql e consegna la query finale.

Claude non si collega al database: chiede di eseguire una query (tool_use),
questo codice la valida e la esegue tramite db.py, e gli rimanda il risultato
(tool_result). Il ciclo continua finché Claude chiama consegna_query.
"""

import json
import logging
import os
import uuid
from functools import lru_cache
from pathlib import Path

import anthropic

from . import consumi, db, impostazioni

# Le credenziali vengono lette dall'ambiente: ANTHROPIC_API_KEY
client = anthropic.Anthropic()

# Modello ed effort si leggono a ogni domanda da impostazioni.correnti(): si cambiano dalla pagina /impostazioni
MAX_PASSI = int(os.getenv("MAX_PASSI", "25"))
MAX_RIGHE_ESPLORAZIONE = int(os.getenv("MAX_RIGHE_ESPLORAZIONE", "50"))
MAX_CARATTERI_CELLA = 200

TOOLS = [
    {
        "name": "esegui_sql",
        "description": (
            "Esegue una query di sola lettura sul database e restituisce al massimo "
            f"{MAX_RIGHE_ESPLORAZIONE} righe. Usala per esplorare la struttura (cataloghi di sistema), "
            "guardare i valori delle colonne e verificare le query (anche con EXPLAIN). "
            "È permessa solo una SELECT o EXPLAIN SELECT per chiamata."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {"sql": {"type": "string", "description": "La query da eseguire"}},
            "required": ["sql"],
            "additionalProperties": False,
        },
    },
    {
        "name": "consegna_query",
        "description": (
            "Consegna all'utente la query SQL finale che risponde alla sua domanda. "
            "La query non verrà eseguita da te: l'utente la eseguirà a parte. "
            "Chiamala una sola volta, quando la query è pronta e verificata."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "sql": {"type": "string", "description": "La query finale, formattata su più righe"},
                "spiegazione": {
                    "type": "string",
                    "description": "Cosa fa la query e quali assunzioni hai fatto, in italiano, in poche frasi",
                },
            },
            "required": ["sql", "spiegazione"],
            "additionalProperties": False,
        },
    },
]


@lru_cache(maxsize=32)  # sempre lo stesso testo per lo stesso database: così la cache dei prompt funziona
def _system_prompt(dialetto: str, solo_metadati: bool) -> str:
    if solo_metadati:
        accesso = (
            "Puoi leggere solo i cataloghi di sistema (la struttura del database), non i dati delle tabelle. "
            "Deduci il significato delle colonne dai nomi, dai tipi, dalle relazioni e dal contesto aziendale."
        )
    else:
        accesso = (
            "Puoi leggere sia i cataloghi di sistema sia i dati. Quando serve, guarda i valori reali "
            "(per esempio SELECT DISTINCT su colonne di stato o di tipo) invece di indovinarli, "
            "ma limita le letture a ciò che ti serve per scrivere la query."
        )

    prompt = f"""Sei un esperto di SQL. L'utente ti fa domande in linguaggio naturale sui dati di un database \
{dialetto} e tu gli consegni la query SQL che risponde alla domanda.

Come lavori:
- Non conosci in anticipo il database: esploralo con esegui_sql interrogando i cataloghi di sistema \
(tabelle, colonne, tipi, chiavi esterne, commenti) finché non conosci le tabelle e le colonne che ti servono.
- {accesso}
- Prima di consegnare, verifica la query con esegui_sql (con EXPLAIN, oppure eseguendola con un LIMIT basso) \
e correggila se il database segnala errori.
- Consegna la query con consegna_query. Usa solo tabelle e colonne che hai visto esistere. \
Scrivi SQL nel dialetto {dialetto}, leggibile e su più righe.
- Se la domanda è ambigua in un modo che cambia davvero il risultato, fai una scelta ragionevole e \
dichiarala nella spiegazione. Se il database non contiene i dati necessari, rispondi in testo senza \
chiamare consegna_query e spiega cosa manca.
- Se l'utente chiede di modificare la query precedente, parti da quella."""

    # Facoltativo: regole di business che non si deducono dal database
    contesto = Path(os.getenv("CONTESTO_PATH", "contesto.md"))
    if contesto.is_file():
        prompt += f"\n\n<contesto_aziendale>\n{contesto.read_text(encoding='utf-8').strip()}\n</contesto_aziendale>"
    return prompt


class ErroreAgente(RuntimeError):
    pass


def genera_query(connessione: dict, domanda: str, storia: list[dict]) -> dict:
    """Trasforma una domanda sul database della connessione in una query SQL.

    `storia` contiene gli scambi precedenti della chat ({"domanda", "risposta"}),
    così l'utente può chiedere modifiche ("ora raggruppa per regione").
    Restituisce {"sql", "spiegazione", "passi", "costo_usd", "modello"} oppure {"testo", "passi", "costo_usd"}.
    """
    messages: list[dict] = []
    for scambio in storia:
        messages.append({"role": "user", "content": scambio["domanda"]})
        messages.append({"role": "assistant", "content": scambio["risposta"]})
    messages.append({"role": "user", "content": domanda})

    # Il dialetto vero lo dice il motore (es. "mssql"); quello salvato nella connessione serve solo da mostrare
    system = _system_prompt(db.motore(connessione).dialect.name, connessione["solo_metadati"])
    passi = []  # le query di esplorazione, da mostrare nell'interfaccia
    richiesta = uuid.uuid4().hex  # lega tra loro, nel registro dei consumi, le chiamate di questa domanda
    costo_usd = 0.0
    scelte = impostazioni.correnti()  # le stesse per tutti i passi di questa domanda
    extra = {}
    if scelte["modello"] in impostazioni.CON_FALLBACK:
        # se il modello rifiuta, Anthropic riprova su un modello alternativo
        extra = {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}
    for _ in range(MAX_PASSI):
        resp = client.beta.messages.create(
            model=scelte["modello"],
            max_tokens=16000,
            system=system,
            tools=TOOLS,
            messages=messages,
            output_config={"effort": scelte["effort"]},
            cache_control={"type": "ephemeral"},  # sistema, strumenti e cronologia vengono riutilizzati tra un passo e l'altro
            **extra,
        )

        # Va registrata prima dei controlli: anche una risposta rifiutata o troncata si paga
        try:
            costo_usd += consumi.registra(richiesta, domanda, resp) or 0
        except Exception:  # un problema del registro non deve bloccare la chat
            logging.exception("Impossibile registrare i consumi")

        if resp.stop_reason == "refusal":
            raise ErroreAgente("Claude ha rifiutato la richiesta. Prova a riformulare la domanda.")
        if resp.stop_reason == "max_tokens":
            raise ErroreAgente("Risposta troppo lunga: prova a fare una domanda più specifica.")

        # La risposta va rimandata così com'è (inclusi i blocchi di ragionamento)
        messages.append({"role": "assistant", "content": resp.content})
        chiamate = [b for b in resp.content if b.type == "tool_use"]

        consegna = next((c for c in chiamate if c.name == "consegna_query"), None)
        if consegna is not None:
            return {"sql": consegna.input["sql"], "spiegazione": consegna.input["spiegazione"], "passi": passi,
                    "costo_usd": costo_usd, "modello": resp.model}

        if not chiamate:
            testo = "\n".join(b.text for b in resp.content if b.type == "text").strip()
            return {"testo": testo or "Non sono riuscito a generare una query.", "passi": passi, "costo_usd": costo_usd}

        risultati = []
        for c in chiamate:
            contenuto, errore = _esegui_tool(connessione, c.name, c.input)
            passi.append({"sql": c.input.get("sql", ""), "esito": "errore" if errore else "ok"})
            risultati.append({"type": "tool_result", "tool_use_id": c.id, "content": contenuto, "is_error": errore})
        messages.append({"role": "user", "content": risultati})

    raise ErroreAgente(f"Nessuna query consegnata dopo {MAX_PASSI} passi. Prova a semplificare la domanda.")


def _esegui_tool(connessione: dict, nome: str, argomenti: dict) -> tuple[str, bool]:
    if nome != "esegui_sql":
        return f"Strumento sconosciuto: {nome}", True
    try:
        r = db.esegui(connessione, argomenti["sql"], MAX_RIGHE_ESPLORAZIONE, solo_metadati=connessione["solo_metadati"])
    except db.QueryNonPermessa as e:
        return f"Query rifiutata: {e}", True
    except Exception as e:  # errore del database: Claude lo legge e corregge la query
        return f"Errore del database: {e}", True
    righe = [[_accorcia(v) for v in riga] for riga in r["righe"]]
    contenuto = json.dumps({"colonne": r["colonne"], "righe": righe}, ensure_ascii=False, default=str)
    if r["troncato"]:
        contenuto += f"\n(mostrate solo le prime {MAX_RIGHE_ESPLORAZIONE} righe)"
    return contenuto, False


def _accorcia(valore):
    if isinstance(valore, str) and len(valore) > MAX_CARATTERI_CELLA:
        return valore[:MAX_CARATTERI_CELLA] + "…"
    return valore

"""Impostazioni modificabili dalla pagina /impostazioni: modello ed effort.

I valori di CLAUDE_MODEL e CLAUDE_EFFORT (file .env) sono i predefiniti; quelli
salvati dalla pagina li sostituiscono e restano anche dopo un riavvio, in un
piccolo file JSON.
"""

import json
import os
import threading
from pathlib import Path

PERCORSO = Path(os.getenv("IMPOSTAZIONI_PATH", "impostazioni.json"))

MODELLO_PREDEFINITO = os.getenv("CLAUDE_MODEL", "claude-opus-5-5")
EFFORT_PREDEFINITO = os.getenv("CLAUDE_EFFORT", "medium")

MODELLI = [
    {"id": "claude-opus-5-5", "nome": "Claude Opus 5.5",
     "descrizione": "Il più preciso nel rapporto qualità/prezzo: consigliato per database grandi o complessi."},
    {"id": "claude-sonnet-5-5", "nome": "Claude Sonnet 5.5",
     "descrizione": "Buon equilibrio tra qualità e costo, circa la metà di Opus."},
    {"id": "claude-haiku-5-5", "nome": "Claude Haiku 5.5",
     "descrizione": "Il più veloce ed economico; meno affidabile sulle domande difficili."},
    {"id": "claude-fable-5-1", "nome": "Claude Fable 5.1",
     "descrizione": "Il più capace in assoluto, ma costa più del doppio di Opus."},
]
# Un modello impostato nel .env ma non in elenco resta comunque selezionabile
if MODELLO_PREDEFINITO not in {m["id"] for m in MODELLI}:
    MODELLI.append({"id": MODELLO_PREDEFINITO, "nome": MODELLO_PREDEFINITO, "descrizione": "Impostato nel file .env."})

EFFORT = [
    {"id": "low", "nome": "Basso", "descrizione": "Più veloce ed economico, esplora meno il database."},
    {"id": "medium", "nome": "Medio", "descrizione": "Il punto di partenza consigliato."},
    {"id": "high", "nome": "Alto", "descrizione": "Ragiona e verifica di più: utile per domande complesse."},
    {"id": "xhigh", "nome": "Molto alto", "descrizione": "Ancora più accurato, più lento e costoso."},
    {"id": "max", "nome": "Massimo", "descrizione": "Quando la correttezza conta più di tempi e costi."},
]

# Modelli che accettano il fallback lato server sui rifiuti (Haiku 5.5 no)
CON_FALLBACK = {"claude-fable-5-1", "claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5"}

_lock = threading.Lock()


class ImpostazioneNonValida(ValueError):
    pass


def correnti() -> dict:
    """Modello ed effort in uso: quelli salvati, oppure i predefiniti del .env."""
    valori = {"modello": MODELLO_PREDEFINITO, "effort": EFFORT_PREDEFINITO}
    with _lock:
        if PERCORSO.is_file():
            try:
                salvati = json.loads(PERCORSO.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                salvati = {}  # file illeggibile: si torna ai predefiniti
            valori.update({k: v for k, v in salvati.items() if k in valori})
    return valori


def salva(modello: str, effort: str) -> dict:
    if modello not in {m["id"] for m in MODELLI}:
        raise ImpostazioneNonValida(f"Modello sconosciuto: {modello}")
    if effort not in {e["id"] for e in EFFORT}:
        raise ImpostazioneNonValida(f"Effort sconosciuto: {effort}")
    with _lock:
        PERCORSO.write_text(json.dumps({"modello": modello, "effort": effort}, indent=2), encoding="utf-8")
    return correnti()


def ripristina() -> dict:
    """Torna ai valori del .env cancellando quelli salvati."""
    with _lock:
        PERCORSO.unlink(missing_ok=True)
    return correnti()

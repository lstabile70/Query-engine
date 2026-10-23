"""Registro dei consumi: i token di ogni chiamata a Claude e il costo stimato.

Il saldo vero dei crediti si legge solo nella console di Anthropic (o con una
chiave Admin): qui il costo è calcolato dai token che l'API restituisce in
`usage`, con i prezzi di listino. È una stima, utile per seguire la spesa.
"""

import os
import sqlite3
import threading
from contextlib import closing
from datetime import datetime, timezone

PERCORSO = os.getenv("CONSUMI_PATH", "consumi.db")
# Facoltativo: il credito acquistato, per stimare quanto ne resta
CREDITO_INIZIALE_USD = float(os.getenv("CREDITO_INIZIALE_USD") or 0)

# USD per milione di token: (input, output, lettura dalla cache).
# La scrittura in cache (durata 5 minuti) costa 1,25 volte l'input.
# Listino di ottobre 2026: se cambia, aggiorna qui (platform.claude.com/docs → Pricing).
PREZZI = {
    "claude-fable-5-1": (10.00, 50.00, 0.25),
    "claude-opus-5-5": (4.00, 20.00, 0.20),
    "claude-opus-5": (5.00, 25.00, 0.50),
    "claude-sonnet-5-5": (2.00, 10.00, 0.20),
    "claude-sonnet-5": (2.00, 10.00, 0.20),
    "claude-haiku-5-5": (0.10, 0.50, 0.01),
}
# Haiku 5.5 costa di più quando il prompt supera i 100.000 token
PREZZI_PROMPT_LUNGO = {"claude-haiku-5-5": ((0.50, 2.50, 0.05), 100_000)}

_lock = threading.Lock()


def _connetti() -> sqlite3.Connection:
    conn = sqlite3.connect(PERCORSO)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """CREATE TABLE IF NOT EXISTS chiamate (
            id INTEGER PRIMARY KEY,
            richiesta TEXT NOT NULL,    -- stesso valore per tutte le chiamate di una domanda
            ora TEXT NOT NULL,          -- UTC, ISO 8601
            domanda TEXT NOT NULL,
            modello TEXT NOT NULL,
            input INTEGER NOT NULL,
            output INTEGER NOT NULL,
            cache_lettura INTEGER NOT NULL,
            cache_scrittura INTEGER NOT NULL,
            costo_usd REAL              -- NULL se il modello non è nel listino
        )"""
    )
    return conn


def costo(modello: str, input_: int, output: int, cache_lettura: int, cache_scrittura: int) -> float | None:
    prezzi = PREZZI.get(modello)
    if prezzi is None:
        return None
    if modello in PREZZI_PROMPT_LUNGO:
        prezzi_alti, soglia = PREZZI_PROMPT_LUNGO[modello]
        if input_ + cache_lettura + cache_scrittura > soglia:
            prezzi = prezzi_alti
    p_in, p_out, p_lettura = prezzi
    return (input_ * p_in + cache_scrittura * p_in * 1.25 + cache_lettura * p_lettura + output * p_out) / 1_000_000


def registra(richiesta: str, domanda: str, resp) -> float | None:
    """Salva i token di una risposta dell'API e restituisce il costo stimato in USD."""
    u = resp.usage
    voci = (
        u.input_tokens or 0,
        u.output_tokens or 0,
        getattr(u, "cache_read_input_tokens", 0) or 0,
        getattr(u, "cache_creation_input_tokens", 0) or 0,
    )
    # resp.model è il modello che ha risposto davvero (può essere quello di riserva)
    usd = costo(resp.model, *voci)
    with _lock, closing(_connetti()) as conn, conn:
        conn.execute(
            "INSERT INTO chiamate (richiesta, ora, domanda, modello, input, output, cache_lettura, cache_scrittura,"
            " costo_usd) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (richiesta, datetime.now(timezone.utc).isoformat(timespec="seconds"), domanda[:500], resp.model,
             *voci, usd),
        )
    return usd


def riepilogo(ultime: int = 50) -> dict:
    """Totali, spesa per giorno e ultime domande, per la pagina dei consumi."""
    with _lock, closing(_connetti()) as conn:
        totale = conn.execute(
            """SELECT COUNT(DISTINCT richiesta) AS domande, COUNT(*) AS chiamate,
                      COALESCE(SUM(input), 0) AS input, COALESCE(SUM(output), 0) AS output,
                      COALESCE(SUM(cache_lettura), 0) AS cache_lettura,
                      COALESCE(SUM(cache_scrittura), 0) AS cache_scrittura,
                      COALESCE(SUM(costo_usd), 0) AS costo_usd,
                      COALESCE(SUM(costo_usd IS NULL), 0) AS senza_prezzo
               FROM chiamate"""
        ).fetchone()
        giorni = conn.execute(
            """SELECT substr(ora, 1, 10) AS giorno, COUNT(DISTINCT richiesta) AS domande,
                      COALESCE(SUM(costo_usd), 0) AS costo_usd
               FROM chiamate GROUP BY giorno ORDER BY giorno DESC LIMIT 31"""
        ).fetchall()
        domande = conn.execute(
            """SELECT MIN(ora) AS ora, MIN(domanda) AS domanda, GROUP_CONCAT(DISTINCT modello) AS modello,
                      COUNT(*) AS chiamate, SUM(input + cache_lettura + cache_scrittura) AS token_input,
                      SUM(output) AS token_output, SUM(costo_usd) AS costo_usd
               FROM chiamate GROUP BY richiesta ORDER BY MIN(ora) DESC LIMIT ?""",
            (ultime,),
        ).fetchall()
    risultato = {
        "totale": dict(totale),
        "giorni": [dict(g) for g in giorni],
        "domande": [dict(d) for d in domande],
        "credito_iniziale_usd": CREDITO_INIZIALE_USD or None,
        "credito_residuo_usd": None,
    }
    if CREDITO_INIZIALE_USD:
        risultato["credito_residuo_usd"] = CREDITO_INIZIALE_USD - totale["costo_usd"]
    return risultato

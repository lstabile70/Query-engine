"""Cifratura delle stringhe di connessione salvate nell'archivio.

La chiave viene da CHIAVE_CIFRATURA e non è mai scritta su disco dall'app: senza
la chiave, chi copia app.db non legge le password dei database. Si genera con
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
Se la chiave cambia, le connessioni salvate con la vecchia non si possono più decifrare.
"""

import os

from cryptography.fernet import Fernet, InvalidToken

_CHIAVE = os.getenv("CHIAVE_CIFRATURA", "").strip()
try:
    _fernet = Fernet(_CHIAVE.encode()) if _CHIAVE else None
except ValueError as e:
    raise RuntimeError("CHIAVE_CIFRATURA non è valida: generane una nuova (vedi README)") from e

ATTIVA = _fernet is not None


class ChiaveMancante(RuntimeError):
    pass


def cifra(testo: str) -> str:
    if _fernet is None:
        raise ChiaveMancante("Per salvare le connessioni imposta CHIAVE_CIFRATURA (vedi README)")
    return _fernet.encrypt(testo.encode()).decode()


def decifra(token: str) -> str:
    if _fernet is None:
        raise ChiaveMancante("Per usare le connessioni salvate imposta CHIAVE_CIFRATURA")
    try:
        return _fernet.decrypt(token.encode()).decode()
    except InvalidToken as e:
        raise ChiaveMancante("Impossibile decifrare la connessione: CHIAVE_CIFRATURA è cambiata?") from e

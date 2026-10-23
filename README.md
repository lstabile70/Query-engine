# Chat SQL

Una web app con una chat: scrivi una domanda in italiano, Claude esplora il tuo
database e ti propone la query SQL che risponde. La query non viene eseguita da
Claude: la copi, oppure premi **Esegui** per vederne i risultati.

```
Browser ──► Server (questa app) ──► API di Claude (Anthropic)
                 │      ▲                 │
                 │      └── "esegui questa SELECT" ┘
                 ▼
           Il tuo database (utente in sola lettura)
```

## Come il server usa Claude

Il server parla con Claude tramite l'**API di Anthropic**, cioè richieste HTTPS
verso `api.anthropic.com` fatte con la libreria ufficiale `anthropic`.

1. Crea un account su [console.anthropic.com](https://console.anthropic.com),
   aggiungi un metodo di pagamento e genera una **API key** (`sk-ant-...`).
2. Passa la chiave al server nella variabile d'ambiente `ANTHROPIC_API_KEY`.
   Non metterla mai nel codice o nel frontend.
3. Il server deve poter uscire su internet verso `api.anthropic.com` (porta 443).

Si paga a consumo, in base ai token. Ogni domanda richiede da 3 a 10 chiamate
(Claude esplora, verifica e poi consegna). Il prompt caching, già attivo nel
codice, riduce molto il costo delle chiamate successive alla prima.

Se usi già AWS o Google Cloud, Claude è disponibile anche tramite Amazon Bedrock
e Vertex AI, fatturato dal tuo cloud. Basta sostituire il client in
`app/agent.py` (`AnthropicBedrockMantle` o `AnthropicVertex`) e togliere il
parametro `fallbacks`, che lì non è supportato.

## Il codice

| File | Cosa fa |
|---|---|
| `app/agent.py` | Il ciclo con Claude: gli dà lo strumento `esegui_sql` per esplorare il DB e `consegna_query` per restituire la query finale |
| `app/db.py` | Esegue le query: accetta solo una SELECT, imposta sola lettura e timeout, limita le righe |
| `app/main.py` | Server web (FastAPI) con password: pagina della chat, `/api/chiedi`, `/api/esegui`, `/consumi` |
| `app/consumi.py` | Registra i token di ogni chiamata a Claude in un file SQLite e ne stima il costo |
| `app/static/index.html` | L'interfaccia della chat |
| `app/static/consumi.html` | La pagina dei consumi: spesa stimata, residuo, token, costo per giorno e per domanda |
| `app/static/stile.css`, `menu.js` | Stile comune (tema chiaro e scuro, layout per telefono) e menu laterale con hamburger |
| `app/impostazioni.py`, `app/static/impostazioni.html` | Scelta e salvataggio di modello ed effort |
| `app/archivio.py` | L'archivio `app.db` (SQLite): schema, aggiornamenti e migrazione dal vecchio `progetti.db` |
| `app/connessioni.py`, `app/static/connessioni.html` | Le connessioni ai database e la pagina per gestirle |
| `app/cifratura.py` | Cifra le stringhe di connessione salvate, con la chiave `CHIAVE_CIFRATURA` |
| `app/progetti.py`, `app/static/query.html` | Progetti e query salvate per ogni connessione, pagina della query salvata |
| `app/static/componenti.js` | SQL colorato, tabella dei risultati ed esportazione CSV, comuni a chat e query salvate |

L'interfaccia non richiede build né librerie da installare. L'unica dipendenza
esterna è [highlight.js](https://highlightjs.org), caricata da cdnjs per colorare
la sintassi SQL: se il browser non raggiunge il CDN, le query restano in chiaro.
| `contesto.md` | Facoltativo: regole di business che Claude non può dedurre dal DB (vedi `contesto.md.esempio`) |

## Provarla sul tuo computer

Serve Python 3.11 o superiore.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python esempio/crea_demo.py          # crea demo.db, un database di prova
cp .env.example .env                 # poi modifica .env:
                                     #   ANTHROPIC_API_KEY=la tua chiave
                                     #   DATABASE_URL=sqlite:///demo.db
                                     #   APP_PASSWORD=una password a scelta
uvicorn app.main:app --env-file .env --port 8080
```

Apri http://localhost:8080, inserisci la password (il nome utente è indifferente)
e prova con "quali sono le 3 regioni con più fatturato nel 2025?".

## Collegare il tuo database

Crea un utente che **può solo leggere**. È la protezione più importante: anche
se una query sfuggisse ai controlli dell'app, il database la rifiuterebbe.

**PostgreSQL**

```sql
CREATE ROLE chat_sql LOGIN PASSWORD 'una-password-robusta';
GRANT CONNECT ON DATABASE miodb TO chat_sql;
GRANT USAGE ON SCHEMA public TO chat_sql;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO chat_sql;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO chat_sql;
```

**MySQL / MariaDB**

```sql
CREATE USER 'chat_sql'@'%' IDENTIFIED BY 'una-password-robusta';
GRANT SELECT ON miodb.* TO 'chat_sql'@'%';
```

Se ci sono tabelle o colonne che Claude non deve vedere, non dare all'utente il
permesso di leggerle: puoi concedere `SELECT` solo su alcune tabelle o su delle viste.

Poi imposta `DATABASE_URL`, ad esempio `postgresql://chat_sql:password@host:5432/miodb`.
Sono già inclusi i driver per PostgreSQL, MySQL e SQLite. Per altri database
(SQL Server, Oracle, ...) aggiungi il driver di SQLAlchemy corrispondente a `requirements.txt`.

Il codice è stato provato con SQLite e PostgreSQL 16.

## Pubblicarla nel cloud

L'app è un normale container Docker. Due requisiti di rete:

- il server deve raggiungere il database: stessa rete privata (VPC), oppure IP del server autorizzato nel firewall del DB;
- il server deve raggiungere `api.anthropic.com`.

### Opzione A: una macchina virtuale (qualsiasi provider)

Su una VM con Docker (AWS EC2, Google Compute Engine, Azure, Hetzner, DigitalOcean, ...):

```bash
docker build -t chat-sql .
docker run -d --restart unless-stopped --env-file .env -p 127.0.0.1:8080:8080 chat-sql
```

Davanti all'app metti un reverse proxy con HTTPS, altrimenti la password viaggia
in chiaro. Il più semplice è [Caddy](https://caddyserver.com), che ottiene da
solo il certificato. Con un dominio che punta alla VM, basta un `Caddyfile` così:

```
chat.tuodominio.it {
    reverse_proxy 127.0.0.1:8080
}
```

### Opzione B: un servizio che esegue container

Google Cloud Run, AWS App Runner, Azure Container Apps, Render, Railway, Fly.io:
carichi il repository o l'immagine Docker, imposti le variabili d'ambiente dal
pannello del servizio, e l'HTTPS è già incluso. L'app ascolta sulla porta
indicata dalla variabile `PORT` (8080 per impostazione predefinita).

Salva `ANTHROPIC_API_KEY`, `DATABASE_URL` e `APP_PASSWORD` nel gestore dei
segreti del servizio, non nell'immagine.

## Configurazione

| Variabile | Obbligatoria | Significato |
|---|---|---|
| `ANTHROPIC_API_KEY` | sì | Chiave dell'API di Anthropic |
| `DATABASE_URL` | sì | Connessione al database, con l'utente in sola lettura. Diventa la prima connessione dell'app |
| `APP_PASSWORD` | sì | Password per accedere alla chat |
| `CLAUDE_MODEL` | no | Modello predefinito: `claude-opus-5-5` (predefinito, il più preciso), `claude-sonnet-5-5` (più economico), `claude-haiku-5-5` (il più economico). Si cambia anche dalla pagina Impostazioni |
| `CLAUDE_EFFORT` | no | Quanto ragiona Claude, predefinito: `low`, `medium` (predefinito), `high`, `xhigh`, `max`. Si cambia anche dalla pagina Impostazioni |
| `SOLO_METADATI` | no | `true`: Claude vede solo la struttura del DB, mai i dati |
| `MAX_RIGHE_ESPLORAZIONE` | no | Righe massime che Claude legge per query (50) |
| `MAX_RIGHE_RISULTATI` | no | Righe massime mostrate con "Esegui" (500) |
| `TIMEOUT_SECONDI` | no | Durata massima di ogni query (15) |
| `CONTESTO_PATH` | no | File con le regole di business (`contesto.md`) |
| `CREDITO_INIZIALE_USD` | no | Credito acquistato: la pagina dei consumi mostra quanto ne resta (stima) |
| `CONSUMI_PATH` | no | File SQLite del registro dei consumi (`consumi.db`) |
| `IMPOSTAZIONI_PATH` | no | File dove la pagina Impostazioni salva modello ed effort (`impostazioni.json`) |
| `ADMIN_PASSWORD` | no | Password per creare, modificare ed eliminare connessioni. Senza, la pagina Connessioni è in sola lettura |
| `CHIAVE_CIFRATURA` | no | Chiave che cifra le password dei database salvate (vedi "Più database"). Senza, non si salvano connessioni |
| `DATI_PATH` | no | Archivio SQLite con connessioni, progetti e query salvate (`app.db`) |
| `PROGETTI_PATH` | no | Vecchio archivio dei progetti (`progetti.db`): al primo avvio viene copiato in `app.db` |

## Progetti e query salvate

Sotto ogni query proposta c'è **Salva**: scegli un titolo e un progetto (o ne
crei uno al volo). Si salvano la query, la domanda, la spiegazione e il database
su cui è stata scritta, **mai i risultati**.

I progetti compaiono nel menu a sinistra come cartelle: **+** crea un progetto,
**⋯** su un progetto lo rinomina o lo elimina (con tutte le sue query). Con il
mouse puoi trascinare una query da un progetto all'altro (su telefono e tablet
usa "Sposta" nella pagina della query). Aprendo
una query la puoi eseguire, copiare, rinominare, spostare in un altro progetto
o eliminare. Se è stata scritta per un database diverso da quello collegato,
la pagina lo segnala.

## Più database

L'app è pensata per lavorare con più database. Ogni **connessione** ha i suoi
progetti e le sue query; il database attivo si sceglie dal selettore in cima al
menu (la scelta resta nel browser) e la chat lavora su quello. Una query salvata
si esegue sempre sul database del suo progetto.

La prima connessione è quella di `DATABASE_URL`, con le opzioni `SOLO_METADATI`
e `TIMEOUT_SECONDI`: la sua stringa non viene mai salvata nell'archivio e si
modifica solo nel file `.env`.

Le altre si gestiscono dalla pagina **Connessioni** (in fondo al menu), con i
campi del modulo (tipo, server, database, utente, password) o con una stringa
di connessione SQLAlchemy. **Prova connessione** controlla il collegamento, la
versione del server e se l'utente ha permessi di scrittura: in quel caso
compare un avviso, perché l'app va usata con utenti in sola lettura. Ogni
connessione ha le sue opzioni "solo metadati" e timeout.

Per attivare la gestione servono due variabili:

- `ADMIN_PASSWORD`: la pagina la chiede prima di creare, modificare, provare
  dati nuovi o eliminare. Chi conosce solo `APP_PASSWORD` può usare i database
  ma non aggiungerne, quindi non può puntare l'app su altri server della rete.
- `CHIAVE_CIFRATURA`: cifra le stringhe di connessione salvate in `app.db`, così
  chi copia il file non legge le password. Si genera con
  `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
  Conservala in un posto sicuro: se la perdi o la cambi, le connessioni salvate
  vanno reinserite.

Le password non tornano mai al browser: modificando una connessione, lasciare
vuoto il campo password (o `***` nella stringa) mantiene quella salvata.
Eliminando una connessione si eliminano i suoi progetti e le sue query, non il
database.

Al primo avvio con questa versione, se esiste `progetti.db`, viene copiato in
`app.db` e i progetti vengono assegnati alla connessione di `DATABASE_URL`; il
vecchio file resta com'era e, verificato che tutto sia a posto, si può cancellare.

Tutto è in `app.db`. La password dell'app è unica, quindi chi accede vede
e modifica gli stessi progetti.

## Impostazioni

Dalla pagina **Impostazioni** (in fondo al menu) scegli modello ed effort. Le
scelte valgono dalla domanda successiva, senza riavviare, e restano salvate in
`impostazioni.json`. **Ripristina predefiniti** cancella il file e torna ai
valori di `CLAUDE_MODEL` e `CLAUDE_EFFORT`.

## Consumi

La pagina `/consumi` (link "Consumi" in alto nella chat) mostra quanto ha speso
l'app: totale, residuo stimato, token, costo per giorno e per domanda. Sotto
ogni risposta compare anche il costo di quella domanda.

È una **stima**: il costo è calcolato dai token che l'API restituisce a ogni
chiamata, con il listino scritto in `app/consumi.py` (da aggiornare se i prezzi
cambiano). Conta solo le chiamate fatte da questa app. Il saldo esatto è nella
console di Anthropic, in Impostazioni → Fatturazione.

## Sicurezza e dati

- **Le barriere contro le modifiche sono tre**: l'utente del database ha solo
  permessi di lettura; ogni connessione è impostata in sola lettura e con un
  timeout (PostgreSQL, MySQL, SQLite); ogni query viene analizzata e sono
  ammesse solo singole `SELECT` (o `EXPLAIN SELECT`).
- **Cosa arriva ad Anthropic**: la domanda, la struttura del database e le
  righe lette da Claude durante l'esplorazione (al massimo 50 per query). Con
  `SOLO_METADATI=true` Claude può leggere solo i cataloghi di sistema, quindi
  nessun dato delle tabelle lascia il tuo server. I risultati di **Esegui** non
  vengono mai inviati a Claude.
- **Accesso alla chat**: protetto da `APP_PASSWORD`. Per più utenti con
  permessi diversi, sostituisci l'autenticazione in `app/main.py` con quella
  aziendale (per esempio un login SSO davanti all'app).

## Migliorare la qualità delle query

Claude esplora da solo tabelle, colonne e valori. Quello che non può scoprire
sono le regole di business: cosa significa "fatturato", quali ordini contano,
quali clienti escludere. Scrivile in `contesto.md`: poche righe precise valgono
più di qualsiasi altra modifica. Quando l'app sbaglia una domanda, chiediti
quale regola mancava e aggiungila lì.

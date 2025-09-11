# Trading Agents Crypto — Setup & Comandi (IT)

Questa guida pratica elenca tutti i comandi necessari per preparare l'ambiente, avviare l'app web, usare la CLI e (opzionale) avviare via Docker. Si assume che tu abbia già compilato correttamente il file `.env`.

## Prerequisiti
- Python 3.10+ (consigliato 3.11)
- Git
- (Opzionale) Docker

## 1) Clonazione e ambiente virtuale
```bash
git clone <URL_DEL_REPO>
cd TradingAgents-crypto

# Linux/macOS
python3 -m venv .venv && source .venv/bin/activate

# Windows (PowerShell)
py -3 -m venv .venv; .\.venv\Scripts\Activate

# Aggiorna pip
python -m pip install --upgrade pip
```

## 2) Installazione dipendenze
- Solo Web App (più leggero):
```bash
pip install -r requirements_web.txt
```
- Tutto il pacchetto (Web + CLI + extra):
```bash
pip install -r requirements.txt
```

## 3) Configurazione variabili d'ambiente (.env)
Assicurati di avere `.env` pronto (puoi partire da `.env.example`). L'app carica automaticamente `.env` all'avvio tramite `python-dotenv`, quindi non servono wrapper speciali sui comandi. In produzione usa sempre un `SECRET_KEY` robusto (casuale a 64+ caratteri esadecimali).

## 4) Avvio Web App (locale)
Hai due opzioni equivalenti. Consigliata: `web_app.py` (rispetta la porta da `PORT`).

### Opzione A — Avvio con `web_app.py` (consigliato)
```bash
python web_app.py
```
- Porta: prende `PORT` da `.env` (default 8080). Apri http://localhost:8080

### Opzione B — Avvio con `run_web.py` (porta 5000 fissa)
```bash
python run_web.py
```
- Porta: 5000. Apri http://localhost:5000

## 5) CLI interattiva (facoltativa)
Per l'interfaccia CLI/tui è consigliato installare tutte le dipendenze:
```bash
pip install -r requirements.txt

# Avvio CLI
python -m cli.main analyze
```

## 6) Esecuzione rapida degli script di test (facoltativo)
- Test funzioni crypto di base (CoinGecko, ecc.):
```bash
python test_crypto.py
```
- Test di base Binance client (modalità):
```bash
python test_binance_trader.py
```

## 7) Docker (opzionale)
Build e run della Web App in container:
```bash
# Build immagine
docker build -t tradingagents-crypto .

# Avvio (passa il tuo .env al container)
docker run --env-file .env -p 8080:8080 tradingagents-crypto
```
Apri http://localhost:8080

## Note utili
- Variabili chiave in `.env` tipiche: `SECRET_KEY`, `ENVIRONMENT`, `PORT`, `FINNHUB_API_KEY`, `TRADING_MODE`, `BINANCE_API_KEY`, `BINANCE_API_SECRET`.
- Le chiavi per i provider LLM sono gestite dall'interfaccia (quando richieste) o da variabili d'ambiente dedicate se previste.
- Per cambi di porta in Docker, modifica `-p <porta_locale>:8080`.
- Per ambienti server, imposta `ENVIRONMENT=production` e usa un `SECRET_KEY` forte.

## Problemi comuni
- Porta occupata: cambia `PORT` nel `.env` (se usi `web_app.py`) o libera la 5000 se usi `run_web.py`.
- Variabili non caricate: verifica l'uso del prefisso `python -m dotenv run -f .env -- ...` o esportale manualmente.
- Mancano dipendenze: verifica di aver usato il requirements corretto (`requirements_web.txt` per Web, `requirements.txt` per Web+CLI).

---
Per deployment su Vercel o cloud, vedi anche `VERCEL_DEPLOYMENT.md`.

FROM python:3.13-slim

WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
# contesto.md è facoltativo: se esiste viene copiato insieme al resto
COPY contesto.md* ./

RUN useradd --create-home appuser && mkdir /srv/dati && chown appuser /srv/dati
USER appuser

# Consumi, impostazioni e progetti: monta un volume su /srv/dati per non perderli quando ricrei il container
ENV CONSUMI_PATH=/srv/dati/consumi.db
ENV IMPOSTAZIONI_PATH=/srv/dati/impostazioni.json
ENV DATI_PATH=/srv/dati/app.db
ENV PROGETTI_PATH=/srv/dati/progetti.db
ENV PORT=8080
EXPOSE 8080
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]

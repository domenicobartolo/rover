FROM python:3.11-slim

# Dipendenze di sistema: ffmpeg serve a faster-whisper/ctranslate2 per la gestione audio
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .

# Modello whisper da usare (tiny/base/small/medium/large-v3), device e tipo di calcolo
ENV WHISPER_MODEL=small \
    WHISPER_DEVICE=cpu \
    WHISPER_COMPUTE_TYPE=int8 \
    WHISPER_LANGUAGE=it \
    HOST=0.0.0.0 \
    PORT=8765

EXPOSE 8765

CMD ["python", "server.py"]

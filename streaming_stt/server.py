"""
Streaming STT WebSocket Server
==============================
Riceve audio PCM 16-bit mono 16kHz a chunk via WebSocket e restituisce
le trascrizioni in tempo (quasi) reale usando faster-whisper.

Protocollo:
- Il client si connette a ws://<host>:8765
- Invia messaggi binari contenenti audio PCM raw (16-bit signed LE, mono, 16000 Hz)
- Quando vuole forzare la trascrizione del buffer accumulato, invia il messaggio
  testuale "EOS" (end of stream / end of segment)
- Il server risponde con messaggi JSON: {"text": "...", "partial": true/false}
- Chiudendo la connessione, il buffer residuo viene trascritto e inviato come finale
"""

import asyncio
import json
import logging
import os

import numpy as np
import websockets
from faster_whisper import WhisperModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("streaming_stt")

# --- Configurazione (personalizzabile via variabili d'ambiente) ---
MODEL_SIZE = os.getenv("WHISPER_MODEL", "small")          # tiny, base, small, medium, large-v3
DEVICE = os.getenv("WHISPER_DEVICE", "cpu")                # cpu oppure cuda
COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")   # int8 (cpu) / float16 (gpu) / float32
LANGUAGE = os.getenv("WHISPER_LANGUAGE", "it")              # None per auto-detect
SAMPLE_RATE = 16000
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8765"))

# Ogni quanti secondi di audio accumulato tentare una trascrizione "parziale"
PARTIAL_INTERVAL_SEC = float(os.getenv("PARTIAL_INTERVAL_SEC", "3.0"))

log.info(f"Carico il modello Whisper '{MODEL_SIZE}' (device={DEVICE}, compute_type={COMPUTE_TYPE})...")
model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
log.info("Modello caricato.")


def transcribe_pcm(pcm_bytes: bytes) -> str:
    """Trascrive un buffer PCM 16-bit mono 16kHz e ritorna il testo concatenato."""
    if len(pcm_bytes) == 0:
        return ""
    audio = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
    segments, _info = model.transcribe(
        audio,
        language=LANGUAGE,
        beam_size=5,
        vad_filter=True,
    )
    return " ".join(seg.text.strip() for seg in segments).strip()


async def handle_client(websocket):
    log.info(f"Client connesso: {websocket.remote_address}")
    buffer = bytearray()
    bytes_per_sec = SAMPLE_RATE * 2  # 16-bit = 2 byte per campione
    partial_threshold = int(bytes_per_sec * PARTIAL_INTERVAL_SEC)

    try:
        async for message in websocket:
            if isinstance(message, str):
                if message == "EOS":
                    text = transcribe_pcm(bytes(buffer))
                    buffer.clear()
                    if text:
                        await websocket.send(json.dumps({"text": text, "partial": False}))
                continue

            # Messaggio binario: chunk audio
            buffer.extend(message)

            if len(buffer) >= partial_threshold:
                text = transcribe_pcm(bytes(buffer))
                if text:
                    await websocket.send(json.dumps({"text": text, "partial": True}))
                buffer.clear()

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        if buffer:
            text = transcribe_pcm(bytes(buffer))
            if text:
                try:
                    await websocket.send(json.dumps({"text": text, "partial": False}))
                except Exception:
                    pass
        log.info(f"Client disconnesso: {websocket.remote_address}")


async def main():
    log.info(f"Avvio server WebSocket su {HOST}:{PORT}")
    async with websockets.serve(handle_client, HOST, PORT, max_size=None):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())

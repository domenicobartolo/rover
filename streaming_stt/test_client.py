"""
Client di test per il server streaming STT.

Uso:
    python test_client.py path/al/file.wav

Requisiti locali (sulla tua macchina, non nel container):
    pip install websockets soundfile numpy

Il file WAV deve essere leggibile da soundfile; viene automaticamente
ricampionato a 16kHz mono se necessario (richiede anche 'librosa' o 'scipy'
per il resampling — qui usiamo un resample semplice con numpy se serve).
"""

import asyncio
import sys
import json

import numpy as np
import soundfile as sf
import websockets

SERVER_URL = "ws://localhost:8765"
CHUNK_MS = 250  # invia audio a blocchi di 250ms, come farebbe un microfono live


def load_audio_16k_mono(path):
    data, sr = sf.read(path, dtype="int16")
    if data.ndim > 1:
        data = data.mean(axis=1).astype(np.int16)
    if sr != 16000:
        # Resample semplice (per test rapidi; per produzione usare librosa/soxr)
        duration = len(data) / sr
        target_len = int(duration * 16000)
        x_old = np.linspace(0, 1, len(data))
        x_new = np.linspace(0, 1, target_len)
        data = np.interp(x_new, x_old, data).astype(np.int16)
    return data


async def run(path):
    audio = load_audio_16k_mono(path)
    chunk_samples = int(16000 * (CHUNK_MS / 1000))

    async with websockets.connect(SERVER_URL, max_size=None) as ws:

        async def receiver():
            async for msg in ws:
                data = json.loads(msg)
                tag = "[PARZIALE]" if data.get("partial") else "[FINALE]  "
                print(f"{tag} {data['text']}")

        recv_task = asyncio.create_task(receiver())

        for i in range(0, len(audio), chunk_samples):
            chunk = audio[i : i + chunk_samples].tobytes()
            await ws.send(chunk)
            await asyncio.sleep(CHUNK_MS / 1000)  # simula tempo reale

        await ws.send("EOS")
        await asyncio.sleep(2)  # tempo per ricevere l'ultima trascrizione
        recv_task.cancel()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python test_client.py path/al/file.wav")
        sys.exit(1)
    asyncio.run(run(sys.argv[1]))

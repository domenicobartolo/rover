"""
streaming_stt/main.py

Pipeline reale di speech-to-text per il controllo vocale del rover.

Flusso:
    microfono -> registrazione audio -> trascrizione (Whisper) ->
    interpretazione comando (vocabolario chiuso) -> publish MQTT
    sul topic comando/interpretato, secondo lo schema in
    docs/interface_contract.md

Vocabolario chiuso supportato:
    - fermati                (nessun parametro)
    - avvicinati <distanza>  (target_distance_m)
    - allontanati <distanza> (target_distance_m)
    - mantieni_distanza <distanza> (target_distance_m)

Uso:
    python main.py                       # loop continuo, push-to-talk (INVIO per registrare)
    python main.py --once                # registra una volta sola ed esce
    python main.py --duration 4          # secondi di registrazione (default 4)
    python main.py --model small         # modello whisper (tiny/base/small/medium)
    python main.py --mqtt-host localhost # host del broker (default: mosquitto, per uso in container)
"""

import argparse
import csv
import difflib
import json
import math
import os
import re
import sys
import time
import wave
from datetime import datetime

import numpy as np
import paho.mqtt.client as mqtt
import sounddevice as sd
import whisper

# ---------------------------------------------------------------------------
# Configurazione
# ---------------------------------------------------------------------------

TOPIC_OUT = "comando/interpretato"
SAMPLE_RATE = 16000  # Whisper lavora nativamente a 16kHz
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "stt_metrics.csv")

# Vocabolario chiuso: parola/e chiave -> nome comando canonico
CLOSED_VOCAB = {
    "fermati": {"keywords": ["fermati", "fermo", "stop", "arrestati"], "needs_distance": False},
    "avvicinati": {"keywords": ["avvicinati", "avvicina"], "needs_distance": True},
    "allontanati": {"keywords": ["allontanati", "allontana"], "needs_distance": True},
    "mantieni_distanza": {
        "keywords": ["mantieni", "mantenere", "resta a", "stai a", "tieni"],
        "needs_distance": True,
    },
}

# Numeri scritti in italiano -> valore, per frasi tipo "un metro e mezzo"
WORD_NUMBERS = {
    "zero": 0, "un": 1, "uno": 1, "una": 1, "due": 2, "tre": 3, "quattro": 4,
    "cinque": 5, "sei": 6, "sette": 7, "otto": 8, "nove": 9, "dieci": 10,
}

# Suggerimento dato a Whisper per orientare la trascrizione verso il
# vocabolario di dominio (riduce drasticamente errori tipo "avvi ginear").
INITIAL_PROMPT = (
    "Comandi vocali per il controllo di un rover: "
    "avvicinati, allontanati, fermati, mantieni la distanza di un metro."
)

# Soglia di similarità (0-1) sotto la quale il fuzzy match non è affidabile
FUZZY_THRESHOLD = 0.72


# ---------------------------------------------------------------------------
# Registrazione audio
# ---------------------------------------------------------------------------

def record_audio(duration: float, samplerate: int = SAMPLE_RATE) -> np.ndarray:
    """Registra audio mono dal microfono di default per `duration` secondi."""
    print(f"[REC] Parla ora... ({duration:.0f}s)")
    audio = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1, dtype="int16")
    sd.wait()
    print("[REC] Registrazione terminata.")
    return audio.flatten()


def check_audio_level(audio: np.ndarray) -> None:
    """Stampa un avviso se il volume registrato è troppo basso: aiuta a
    distinguere un problema di microfono/VM da un problema del modello."""
    rms = float(np.sqrt(np.mean(audio.astype(np.float64) ** 2)))
    peak = int(np.max(np.abs(audio))) if audio.size else 0
    print(f"[REC] Livello audio: RMS={rms:.1f}, picco={peak} (max possibile 32767)")
    if peak < 500:
        print(
            "[REC][ATTENZIONE] Volume molto basso: probabile problema di "
            "microfono/passthrough audio della VM, non del modello Whisper. "
            "Controlla il volume di input del sistema o avvicina il microfono."
        )


def save_wav(audio: np.ndarray, path: str, samplerate: int = SAMPLE_RATE) -> None:
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # int16 -> 2 byte
        wf.setframerate(samplerate)
        wf.writeframes(audio.tobytes())


# ---------------------------------------------------------------------------
# Interpretazione del comando (vocabolario chiuso)
# ---------------------------------------------------------------------------

def parse_distance(text: str):
    """Estrae una distanza in metri dal testo, se presente."""
    text = text.lower()

    # Caso numerico esplicito: "1.5 metri", "2 metri", "1,5 m"
    match = re.search(r"(\d+[.,]?\d*)\s*(metri|metro|m)\b", text)
    if match:
        return float(match.group(1).replace(",", "."))

    # Caso testuale: "un metro e mezzo", "due metri"
    for word, val in WORD_NUMBERS.items():
        if re.search(rf"\b{word}\b\s*metr", text):
            if "mezzo" in text or "mezza" in text:
                val += 0.5
            return float(val)

    return None


def parse_command(text: str):
    """
    Interpreta il testo trascritto secondo il vocabolario chiuso.
    Ritorna (comando|None, params dict).
    Se nessun comando valido viene riconosciuto, comando è None:
    Antonio (validazione lato MQTT/ROS) deve scartare questi messaggi.

    Prova prima un match esatto (sottostringa), poi un fuzzy match
    parola per parola: utile quando Whisper trascrive in modo
    leggermente errato una parola del vocabolario (es. "avvi ginear"
    al posto di "avvicinati").
    """
    t = text.lower()

    # 1. Match esatto (sottostringa)
    for command, info in CLOSED_VOCAB.items():
        if any(kw in t for kw in info["keywords"]):
            distance = parse_distance(t) if info["needs_distance"] else None
            params = {"target_distance_m": distance} if distance is not None else {}
            return command, params

    # 2. Fuzzy match: confronta ogni parola del testo con ogni keyword
    words = re.findall(r"[a-zàèéìòù]+", t)
    best_command, best_score = None, 0.0
    for command, info in CLOSED_VOCAB.items():
        for kw in info["keywords"]:
            kw_first_word = kw.split()[0]  # gestisce keyword multi-parola tipo "resta a"
            matches = difflib.get_close_matches(kw_first_word, words, n=1, cutoff=0.0)
            if matches:
                score = difflib.SequenceMatcher(None, kw_first_word, matches[0]).ratio()
                if score > best_score:
                    best_score, best_command = score, command

    if best_command and best_score >= FUZZY_THRESHOLD:
        info = CLOSED_VOCAB[best_command]
        distance = parse_distance(t) if info["needs_distance"] else None
        params = {"target_distance_m": distance} if distance is not None else {}
        print(f"[PARSE] Match approssimato ({best_score:.2f}) -> {best_command}")
        return best_command, params

    return None, {}


def estimate_confidence(result: dict) -> float:
    """
    Stima una confidenza approssimata [0-1] dalla trascrizione Whisper,
    usando l'avg_logprob medio dei segmenti (metrica euristica, non è
    una probabilità calibrata, ma è utile come indicatore relativo).
    """
    segments = result.get("segments", [])
    if not segments:
        return 0.0
    avg_logprob = sum(s.get("avg_logprob", -1.0) for s in segments) / len(segments)
    # avg_logprob è tipicamente negativo (es. -0.2 buono, -1.5 scarso)
    confidence = math.exp(avg_logprob)
    return round(min(max(confidence, 0.0), 1.0), 3)


# ---------------------------------------------------------------------------
# Logging metriche (per la relazione tecnica: accuratezza/tempo STT)
# ---------------------------------------------------------------------------

def log_metrics(raw_text, command, params, stt_confidence, elapsed_ms):
    os.makedirs(LOG_DIR, exist_ok=True)
    file_exists = os.path.isfile(LOG_FILE)
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(
                ["timestamp", "raw_text", "command", "params", "stt_confidence", "elapsed_ms"]
            )
        writer.writerow(
            [datetime.now().isoformat(), raw_text, command, json.dumps(params), stt_confidence, elapsed_ms]
        )


# ---------------------------------------------------------------------------
# MQTT
# ---------------------------------------------------------------------------

def publish_command(client: mqtt.Client, command, params, raw_text, stt_confidence):
    message = {
        "timestamp": time.time(),
        "command": command,  # None se non riconosciuto -> Antonio deve scartarlo
        "params": params,
        "raw_text": raw_text,
        "stt_confidence": stt_confidence,
        "interpreter": "rule_based",
    }
    client.publish(TOPIC_OUT, json.dumps(message))
    print(f"[MQTT] Pubblicato su {TOPIC_OUT}: {message}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Speech-to-text -> comando ROS via MQTT")
    parser.add_argument("--duration", type=float, default=4.0, help="Secondi di registrazione")
    parser.add_argument("--model", type=str, default="base", help="Modello Whisper (tiny/base/small/medium)")
    parser.add_argument("--language", type=str, default="it", help="Lingua per la trascrizione")
    parser.add_argument(
        "--mqtt-host",
        type=str,
        default=os.environ.get("MQTT_HOST", "mosquitto"),
        help="Host del broker MQTT (usa 'localhost' se esegui fuori dal container)",
    )
    parser.add_argument("--mqtt-port", type=int, default=1883)
    parser.add_argument("--once", action="store_true", help="Esegue una sola registrazione ed esce")
    parser.add_argument(
        "--list-devices", action="store_true", help="Elenca i dispositivi audio disponibili ed esce"
    )
    args = parser.parse_args()

    if args.list_devices:
        print(sd.query_devices())
        sys.exit(0)

    print(f"[INIT] Caricamento modello Whisper '{args.model}'...")
    model = whisper.load_model(args.model)
    print("[INIT] Modello caricato.")

    client = mqtt.Client()
    client.connect(args.mqtt_host, args.mqtt_port, keepalive=60)
    client.loop_start()

    os.makedirs("tmp_audio", exist_ok=True)

    try:
        while True:
            if not args.once:
                input("\nPremi INVIO per registrare un comando (Ctrl+C per uscire)...")

            audio = record_audio(args.duration)
            check_audio_level(audio)
            wav_path = os.path.join("tmp_audio", "last_command.wav")
            save_wav(audio, wav_path)

            start = time.time()
            result = model.transcribe(
                wav_path, language=args.language, fp16=False, initial_prompt=INITIAL_PROMPT
            )
            elapsed_ms = round((time.time() - start) * 1000, 1)

            raw_text = result["text"].strip()
            stt_confidence = estimate_confidence(result)
            command, params = parse_command(raw_text)

            print(f"[STT] Testo trascritto: \"{raw_text}\" (confidenza~{stt_confidence}, {elapsed_ms}ms)")
            if command:
                print(f"[PARSE] Comando riconosciuto: {command} {params}")
            else:
                print("[PARSE] Nessun comando valido riconosciuto nel vocabolario chiuso.")

            publish_command(client, command, params, raw_text, stt_confidence)
            log_metrics(raw_text, command, params, stt_confidence, elapsed_ms)

            if args.once:
                break

    except KeyboardInterrupt:
        print("\n[EXIT] Interrotto dall'utente.")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()

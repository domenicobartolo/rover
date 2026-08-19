"""
Bridge MQTT/ROS2: riceve percezione/detection e comando/interpretato,
valida il comando secondo il vocabolario chiuso, la distanza minima
di sicurezza e la freschezza del dato (timeout), e pubblica il
risultato su rover/comando_validato con la latenza end-to-end.
"""
import json
import time
import paho.mqtt.client as mqtt

BROKER_HOST = "mosquitto"
BROKER_PORT = 1883

TOPIC_DETECTION = "percezione/detection"
TOPIC_COMMAND = "comando/interpretato"
TOPIC_VALIDATED = "rover/comando_validato"

COMANDI_VALIDI = {"avvicinati", "allontanati", "fermati", "mantieni_distanza"}
DISTANZA_MINIMA_SICUREZZA_M = 0.5
TIMEOUT_DETECTION_S = 3.0

ultima_distanza_m = None
ultimo_timestamp_detection = None

def on_connect(client, userdata, flags, rc):
    print(f"Connesso al broker con codice {rc}")
    client.subscribe(TOPIC_DETECTION)
    client.subscribe(TOPIC_COMMAND)

def on_message(client, userdata, msg):
    global ultima_distanza_m, ultimo_timestamp_detection
    payload = json.loads(msg.payload.decode())

    if msg.topic == TOPIC_DETECTION:
        detections = payload.get("detections", [])
        if detections:
            ultima_distanza_m = detections[0].get("distance_m")
            ultimo_timestamp_detection = payload.get("timestamp", time.time())
            print(f"Aggiornata distanza nota: {ultima_distanza_m} m")

    elif msg.topic == TOPIC_COMMAND:
        print(f"Ricevuto comando: {payload}")
        validato, motivo = valida_comando(payload)

        ts_origine = payload.get("timestamp", time.time())
        latenza_ms = round((time.time() - ts_origine) * 1000, 1)

        risultato = {
            "timestamp": time.time(),
            "action": payload.get("command"),
            "target_distance_m": payload.get("params", {}).get("target_distance_m"),
            "validated": validato,
            "rejection_reason": motivo,
            "latency_pipeline_ms": latenza_ms,
        }
        client.publish(TOPIC_VALIDATED, json.dumps(risultato))
        print(f"Pubblicato su {TOPIC_VALIDATED}: {risultato}")

def valida_comando(payload):
    comando = payload.get("command")

    if comando not in COMANDI_VALIDI:
        return False, f"comando '{comando}' non riconosciuto"

    if comando == "fermati":
        return True, None

    if comando in {"avvicinati", "mantieni_distanza"}:
        if ultimo_timestamp_detection is None:
            return False, "nessuna detection ricevuta finora, impossibile validare"

        eta_detection_s = time.time() - ultimo_timestamp_detection
        if eta_detection_s > TIMEOUT_DETECTION_S:
            return False, f"detection obsoleta (vecchia di {eta_detection_s:.1f}s, limite {TIMEOUT_DETECTION_S}s)"

    if comando == "avvicinati":
        target = payload.get("params", {}).get("target_distance_m")
        if target is not None and target < DISTANZA_MINIMA_SICUREZZA_M:
            return False, f"target_distance_m {target} sotto la soglia minima di sicurezza ({DISTANZA_MINIMA_SICUREZZA_M} m)"

    return True, None

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
client.loop_forever()

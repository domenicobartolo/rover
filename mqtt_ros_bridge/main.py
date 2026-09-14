"""
Bridge MQTT/ROS2: riceve percezione/detection e comando/interpretato,
valida il comando secondo il vocabolario chiuso, la presenza/freschezza/
confidenza della detection, la distanza minima di sicurezza e la
coerenza tra il comando richiesto e la distanza attuale nota.
Pubblica il risultato su rover/comando_validato con la latenza end-to-end.
"""
import json
import os
import time
import paho.mqtt.client as mqtt

BROKER_HOST = os.environ.get("MQTT_BROKER_HOST", "mosquitto")
BROKER_PORT = int(os.environ.get("MQTT_BROKER_PORT", 1883))

PREFIX = "rover-gruppo4-domenico-test"

TOPIC_DETECTION = f"{PREFIX}/percezione/detection"
TOPIC_COMMAND = f"{PREFIX}/comando/interpretato"
TOPIC_VALIDATED = f"{PREFIX}/rover/comando_validato"

COMANDI_VALIDI = {"avvicinati", "allontanati", "fermati", "mantieni_distanza"}
DISTANZA_MINIMA_SICUREZZA_M = 0.5
TIMEOUT_DETECTION_S = 3.0
CONFIDENCE_MINIMA = 0.5

ultima_distanza_m = None
ultima_confidence = None
ultimo_person_detected = None
ultimo_timestamp_detection = None

def on_connect(client, userdata, flags, rc):
    print(f"Connesso al broker con codice {rc}")
    client.subscribe(TOPIC_DETECTION)
    client.subscribe(TOPIC_COMMAND)
    print(f"Sottoscritto a: {TOPIC_DETECTION} e {TOPIC_COMMAND}")

def on_message(client, userdata, msg):
    global ultima_distanza_m, ultima_confidence, ultimo_person_detected, ultimo_timestamp_detection
    payload = json.loads(msg.payload.decode())

    if msg.topic == TOPIC_DETECTION:
        ultimo_person_detected = payload.get("person_detected", False)
        ultimo_timestamp_detection = payload.get("timestamp", time.time())

        detections = payload.get("detections", [])
        if detections:
            piu_vicina = min(detections, key=lambda d: d.get("distance_m", float("inf")))
            ultima_distanza_m = piu_vicina.get("distance_m")
            ultima_confidence = piu_vicina.get("confidence")
            print(f"Aggiornata detection: distanza={ultima_distanza_m} m, "
                  f"confidence={ultima_confidence}, persone_rilevate={len(detections)}")
        else:
            ultima_distanza_m = None
            ultima_confidence = None

    elif msg.topic == TOPIC_COMMAND:
        print(f"Ricevuto comando: {payload}")
        validato, motivo, target_effettivo = valida_comando(payload)

        ts_origine = payload.get("timestamp", time.time())
        latenza_ms = round((time.time() - ts_origine) * 1000, 1)

        risultato = {
            "timestamp": time.time(),
            "action": payload.get("command"),
            "target_distance_m": target_effettivo,
            "validated": validato,
            "rejection_reason": motivo,
            "latency_pipeline_ms": latenza_ms,
        }
        client.publish(TOPIC_VALIDATED, json.dumps(risultato))
        print(f"Pubblicato su {TOPIC_VALIDATED}: {risultato}")

def valida_comando(payload):
    comando = payload.get("command")

    if comando not in COMANDI_VALIDI:
        return False, f"comando '{comando}' non riconosciuto", None

    if comando == "fermati":
        return True, None, None

    target = payload.get("params", {}).get("target_distance_m")

    if target is None:
        if comando == "avvicinati":
            target = DISTANZA_MINIMA_SICUREZZA_M
            print(f"target_distance_m mancante per 'avvicinati': applico il default di sicurezza {target} m")
        elif comando == "mantieni_distanza":
            return False, "target_distance_m mancante per 'mantieni_distanza', impossibile validare", None
        elif comando == "allontanati":
            print("target_distance_m mancante per 'allontanati': nessun default applicato, procedo senza vincolo di coerenza")

    if target is not None and not isinstance(target, (int, float)):
        return False, f"target_distance_m non valido: {target}", None

    if target is not None and target < 0:
        return False, f"target_distance_m negativo non valido: {target}", None

    if comando in {"avvicinati", "mantieni_distanza"}:
        if ultimo_timestamp_detection is None:
            return False, "nessuna detection ricevuta finora, impossibile validare", target

        eta_detection_s = time.time() - ultimo_timestamp_detection
        if eta_detection_s > TIMEOUT_DETECTION_S:
            return False, f"detection obsoleta (vecchia di {eta_detection_s:.1f}s, limite {TIMEOUT_DETECTION_S}s)", target

        if not ultimo_person_detected:
            return False, "nessuna persona rilevata al momento", target

        if ultima_confidence is not None and ultima_confidence < CONFIDENCE_MINIMA:
            return False, f"confidence della detection troppo bassa ({ultima_confidence:.2f}, minimo {CONFIDENCE_MINIMA})", target

    if comando == "avvicinati" and target is not None:
        if target < DISTANZA_MINIMA_SICUREZZA_M:
            return False, f"target_distance_m {target} sotto la soglia minima di sicurezza ({DISTANZA_MINIMA_SICUREZZA_M} m)", target

    if comando == "avvicinati" and target is not None and ultima_distanza_m is not None:
        if target >= ultima_distanza_m:
            return False, (f"target {target}m non e' piu' vicino della distanza attuale "
                            f"({ultima_distanza_m:.2f}m): comando incoerente"), target

    if comando == "allontanati" and target is not None and ultima_distanza_m is not None:
        if target <= ultima_distanza_m:
            return False, (f"target {target}m non e' piu' lontano della distanza attuale "
                            f"({ultima_distanza_m:.2f}m): comando incoerente"), target

    return True, None, target

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
import time as time_module

print("Attendo 10 secondi prima del primo tentativo di connessione...")
time_module.sleep(10)

max_tentativi = 15
for tentativo in range(1, max_tentativi + 1):
    try:
        client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
        break
    except (ConnectionRefusedError, OSError) as e:
        print(f"Connessione fallita ({e}) - tentativo {tentativo}/{max_tentativi}, riprovo tra 3 secondi...")
        time_module.sleep(60)
else:
    print("Impossibile connettersi al broker dopo diversi tentativi, esco.")
    exit(1)
for tentativo in range(1, max_tentativi + 1):
    try:
        client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
        break
    except ConnectionRefusedError:
        print(f"Connessione rifiutata (tentativo {tentativo}/{max_tentativi}), riprovo tra 2 secondi...")
        time_module.sleep(2)
else:
    print("Impossibile connettersi al broker dopo diversi tentativi, esco.")
    exit(1)

client.loop_forever()

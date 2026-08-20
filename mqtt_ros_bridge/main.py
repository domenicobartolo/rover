"""
Bridge MQTT/ROS2: riceve percezione/detection e comando/interpretato,
valida il comando secondo il vocabolario chiuso, la presenza/freschezza/
confidenza della detection, la distanza minima di sicurezza e la
coerenza tra il comando richiesto e la distanza attuale nota.
Pubblica il risultato su rover/comando_validato con la latenza end-to-end.
"""
import json
import time
import paho.mqtt.client as mqtt

BROKER_HOST = "broker.hivemq.com"
BROKER_PORT = 1883

PREFIX = "rover-gruppo4-domenico-test"

TOPIC_DETECTION = f"{PREFIX}/percezione/detection"
TOPIC_COMMAND = f"{PREFIX}/comando/interpretato"
TOPIC_VALIDATED = f"{PREFIX}/rover/comando_validato"

COMANDI_VALIDI = {"avvicinati", "allontanati", "fermati", "mantieni_distanza"}
DISTANZA_MINIMA_SICUREZZA_M = 0.5
TIMEOUT_DETECTION_S = 3.0
CONFIDENCE_MINIMA = 0.5

# Stato aggiornato ad ogni messaggio di detection
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
    """
    Ritorna (validato: bool, motivo_rifiuto: str|None, target_effettivo: float|None).
    target_effettivo puo' differire dal target ricevuto se e' stato applicato
    un default di sicurezza (vedi vincolo 2).
    """
    comando = payload.get("command")

    if comando not in COMANDI_VALIDI:
        return False, f"comando '{comando}' non riconosciuto", None

    if comando == "fermati":
        # sempre eseguibile, priorita' massima, non dipende da altri parametri
        return True, None, None

    target = payload.get("params", {}).get("target_distance_m")

    # Vincolo 2: target mancante -> applichiamo un default prudente invece di
    # saltare il controllo di sicurezza (non ci fidiamo che Gregorio lo fornisca sempre)
    if target is None:
        if comando == "avvicinati":
            target = DISTANZA_MINIMA_SICUREZZA_M
            print(f"target_distance_m mancante per 'avvicinati': applico il default di sicurezza {target} m")
        elif comando == "mantieni_distanza":
            return False, "target_distance_m mancante per 'mantieni_distanza', impossibile validare", None
        # per 'allontanati' un target mancante e' meno rischioso (si allontana e basta),
        # ma lo segnaliamo comunque per coerenza dei dati
        elif comando == "allontanati" and target is None:
            print("target_distance_m mancante per 'allontanati': nessun default applicato, procedo senza vincolo di coerenza")

    if not isinstance(target, (int, float)) and target is not None:
        return False, f"target_distance_m non valido: {target}", None

    if target is not None and target < 0:
        return False, f"target_distance_m negativo non valido: {target}", None

    # Vincolo 6/7/8: comandi che dipendono dalla presenza/distanza di una persona rilevata
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

    # Vincolo 3: distanza minima assoluta di sicurezza
    if comando == "avvicinati" and target is not None:
        if target < DISTANZA_MINIMA_SICUREZZA_M:
            return False, f"target_distance_m {target} sotto la soglia minima di sicurezza ({DISTANZA_MINIMA_SICUREZZA_M} m)", target

    # Vincolo 4: coerenza avvicinati -> il target deve essere piu' vicino della distanza attuale
    if comando == "avvicinati" and target is not None and ultima_distanza_m is not None:
        if target >= ultima_distanza_m:
            return False, (f"target {target}m non e' piu' vicino della distanza attuale "
                            f"({ultima_distanza_m:.2f}m): comando incoerente"), target

    # Vincolo 5: coerenza allontanati -> il target deve essere piu' lontano della distanza attuale
    if comando == "allontanati" and target is not None and ultima_distanza_m is not None:
        if target <= ultima_distanza_m:
            return False, (f"target {target}m non e' piu' lontano della distanza attuale "
                            f"({ultima_distanza_m:.2f}m): comando incoerente"), target

    return True, None, target

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
client.loop_forever()

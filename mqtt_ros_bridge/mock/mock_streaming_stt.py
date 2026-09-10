"""
Mock che simula il modulo streaming_stt: pubblica periodicamente
comandi interpretati su comando/interpretato, secondo lo schema
in docs/interface_contract.md. Utile per testare mqtt_ros_bridge
senza dipendere dal modulo STT reale.
"""
import json
import time
import random
import paho.mqtt.client as mqtt

BROKER_HOST = "mosquitto"
BROKER_PORT = 1883
TOPIC = "comando/interpretato"

COMANDI_DI_TEST = [
    {"command": "avvicinati", "params": {"target_distance_m": 1.0}, "raw_text": "avvicinati alla persona"},
    {"command": "avvicinati", "params": {"target_distance_m": 0.2}, "raw_text": "avvicinati tanto"},
    {"command": "allontanati", "params": {"target_distance_m": 3.0}, "raw_text": "allontanati"},
    {"command": "fermati", "params": {}, "raw_text": "fermati"},
    {"command": "mantieni_distanza", "params": {"target_distance_m": 1.5}, "raw_text": "mantieni un metro e mezzo"},
    {"command": "balla", "params": {}, "raw_text": "fai una danza"},
]

client = mqtt.Client()
client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)

while True:
    scelto = random.choice(COMANDI_DI_TEST)
    message = {
        "timestamp": time.time(),
        "command": scelto["command"],
        "params": scelto["params"],
        "raw_text": scelto["raw_text"],
        "stt_confidence": round(random.uniform(0.8, 0.99), 2),
        "interpreter": "rule_based",
    }
    client.publish(TOPIC, json.dumps(message))
    print(f"[mock_streaming_stt] Pubblicato: {message}")
    time.sleep(6)

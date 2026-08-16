"""
Script minimo di verifica: pubblica un messaggio di test sul topic
percezione/detection ogni 2 secondi, secondo lo schema in
docs/interface_contract.md. Serve solo per testare che il container
si costruisca e comunichi correttamente col broker MQTT.
"""
import json
import time
import paho.mqtt.client as mqtt
import os

BROKER_HOST = os.environ.get("MQTT_BROKER_HOST", "localhost")  # nome del servizio nel docker-compose, non "localhost"
BROKER_PORT = 1883
TOPIC = "percezione/detection"

client = mqtt.Client()
client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)

frame_id = 0
while True:
    message = {
        "timestamp": time.time(),
        "frame_id": frame_id,
        "setting": "edge",
        "person_detected": True,
        "detections": [
            {"bbox": [10, 10, 100, 200], "confidence": 0.9, "distance_m": 2.0, "track_id": 1}
        ],
        "inference_time_ms": 40.0,
    }
    client.publish(TOPIC, json.dumps(message))
    print(f"Pubblicato: {message}")
    frame_id += 1
    time.sleep(2)

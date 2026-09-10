"""
Mock che simula il modulo ai_detection: pubblica periodicamente
messaggi di detection su percezione/detection, secondo lo schema
in docs/interface_contract.md. Utile per testare mqtt_ros_bridge
senza dipendere dal modulo AI reale.
"""
import json
import time
import random
import paho.mqtt.client as mqtt

BROKER_HOST = "mosquitto"
BROKER_PORT = 1883
TOPIC = "percezione/detection"
FREQUENZA_HZ = 2  # messaggi al secondo, realistico per la traccia (10-15 Hz in produzione)

client = mqtt.Client()
client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)

frame_id = 0
while True:
    distanza = round(random.uniform(0.5, 4.0), 2)
    message = {
        "timestamp": time.time(),
        "frame_id": frame_id,
        "setting": "edge",
        "person_detected": True,
        "detections": [
            {
                "bbox": [10, 10, 100, 200],
                "confidence": round(random.uniform(0.7, 0.99), 2),
                "distance_m": distanza,
                "track_id": 1,
            }
        ],
        "inference_time_ms": round(random.uniform(20, 60), 1),
    }
    client.publish(TOPIC, json.dumps(message))
    print(f"[mock_ai_detection] Pubblicato: {message}")
    frame_id += 1
    time.sleep(1 / FREQUENZA_HZ)

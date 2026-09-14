"""
Publisher MQTT con human detection reale (YOLOv8n) e stima distanza.
Pubblica su percezione/detection secondo lo schema in
docs/interface_contract.md.
"""
import os
import json
import time
import cv2
import paho.mqtt.client as mqtt
from ultralytics import YOLO
from distance_estimator import estimate_distance

# Configurazione broker: "localhost" in sviluppo locale,
# "mosquitto" quando eseguito dentro il container Docker (vedi docker-compose.yml)
BROKER_HOST = os.environ.get("MQTT_BROKER_HOST", "localhost")
BROKER_PORT = 1883
TOPIC = "percezione/detection"

# "edge" = detection a bordo (questo script); cambiare se eseguito da remoto
SETTING = os.environ.get("DETECTION_SETTING", "edge")

PERSON_CLASS_ID = 0

model = YOLO("yolov8n.pt")


def main():
    client = mqtt.Client()
    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
    print(f"Connesso al broker MQTT {BROKER_HOST}:{BROKER_PORT}")

    cap = cv2.VideoCapture(4)
    if not cap.isOpened():
        print("Errore: impossibile accedere alla webcam")
        return
    print("Detection avviata, pubblicazione su MQTT. Premi Ctrl+C per uscire.")

    frame_id = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            start_time = time.time()
            results = model(frame, verbose=False)
            inference_time_ms = (time.time() - start_time) * 1000

            detections = []
            for result in results:
                for box in result.boxes:
                    if int(box.cls[0]) == PERSON_CLASS_ID:
                        confidence = float(box.conf[0])
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        bbox_height = y2 - y1
                        distance = estimate_distance(bbox_height)

                        detections.append({
                            "bbox": [x1, y1, x2 - x1, y2 - y1],  # formato [x, y, w, h] come da contratto
                            "confidence": round(confidence, 3),
                            "distance_m": distance,
                            "track_id": None,  # tracking non ancora implementato
                        })

            message = {
                "timestamp": time.time(),
                "frame_id": frame_id,
                "setting": SETTING,
                "person_detected": len(detections) > 0,
                "detections": detections,
                "inference_time_ms": round(inference_time_ms, 2),
            }

            client.publish(TOPIC, json.dumps(message))
            print(f"Frame {frame_id}: {len(detections)} persona/e rilevata/e, "
                  f"inferenza {inference_time_ms:.1f}ms")

            frame_id += 1

    except KeyboardInterrupt:
        print("\nInterrotto dall'utente")
    finally:
        cap.release()
        client.disconnect()


if __name__ == "__main__":
    main()

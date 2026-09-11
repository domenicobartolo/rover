"""
Publisher MQTT con human detection (YOLOv8n) tramite mosquitto_pub di sistema.
"""
import os
import json
import time
import subprocess
import cv2
from ultralytics import YOLO
from distance_estimator import estimate_distance

BROKER_HOST = os.environ.get("MQTT_BROKER_HOST", "localhost")
BROKER_PORT = os.environ.get("MQTT_BROKER_PORT", "1883")
TOPIC = "percezione/detection"
SETTING = os.environ.get("DETECTION_SETTING", "edge")
PERSON_CLASS_ID = 0

model = YOLO("yolov8n.pt")


def send_mqtt_message(topic, message_dict):
    """Invia il messaggio usando il comando mosquitto_pub di sistema."""
    payload = json.dumps(message_dict)
    cmd = [
        "mosquitto_pub",
        "-h", BROKER_HOST,
        "-p", str(BROKER_PORT),
        "-t", topic,
        "-m", payload
    ]
    try:
        subprocess.run(cmd, check=True)
    except Exception as e:
        print(f"Errore durante l'invio con mosquitto_pub: {e}")


def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Errore: impossibile accedere alla webcam")
        return

    print(f"Detection avviata. Invio dati a Mosquitto ({BROKER_HOST}:{BROKER_PORT})...")
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
                            "bbox": [x1, y1, x2 - x1, y2 - y1],
                            "confidence": round(confidence, 3),
                            "distance_m": distance,
                            "track_id": None,
                        })

            message = {
                "timestamp": time.time(),
                "frame_id": frame_id,
                "setting": SETTING,
                "person_detected": len(detections) > 0,
                "detections": detections,
                "inference_time_ms": round(inference_time_ms, 2),
            }

            # Invia tramite il comando mosquitto_pub
            send_mqtt_message(TOPIC, message)
            
            print(f"Frame {frame_id}: {len(detections)} persona/e | {inference_time_ms:.1f}ms")
            frame_id += 1
            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\nInterrotto")
    finally:
        cap.release()


if __name__ == "__main__":
    main()

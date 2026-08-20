import cv2
from ultralytics import YOLO
from distance_estimator import estimate_distance
import time
from metrics_logger import MetricsLogger

#import del modello pre-addestrato su COCO
model = YOLO("yolov8n.pt")

#ID della classe persona in coco
PERSON_CLASS_ID=0

def main():
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print ("Errore apertura webcam")
        return
    print("webcam avviata correttamente. Premi q per uscire")

    logger = MetricsLogger("results/metrics_live.csv", "yolov8n")
    frame_id=0
    prev_frame_time = time.time()

    while True:
        ret,frame = cap.read()
        if not ret:
            break
        
        start_time = time.time()
        #inferenza yolo su frame corrente
        results= model(frame, verbose=False)
        inference_time_ms= (time.time()-start_time)*1000

        current_frame_time = time.time()
        fps = 1 / (current_frame_time - prev_frame_time)
        prev_frame_time = current_frame_time

        fps_text = f"Inference: {inference_time_ms:.1f}ms"
        cv2.putText(frame, fps_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        
        num_detections = 0
        confidences = []
        distances = []

        #bounding boxes della persona
        for result in results:
            for box in result.boxes:
                class_id = int(box.cls[0])
                if class_id == PERSON_CLASS_ID:
                    confidence = float(box.conf[0])
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    bb_height = y2-y1
                    distance = estimate_distance(bb_height)
                    num_detections += 1
                    confidences.append(confidence)
                    if distance is not None:
                        distances.append(distance)

                    cv2.rectangle(frame, (x1,y1), (x2,y2), (0,255,0),2)
                    label = f"persona {confidence:.2f} | {distance}m"
                    
                    cv2.putText(frame, label, (x1,y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0),2)

        cv2.imshow("Detection test",frame)

        avg_confidence = round(sum(confidences) / len(confidences), 3) if confidences else 0
        avg_distance = round(sum(distances) / len(distances), 2) if distances else None

        logger.log_frame(frame_id, time.time(), num_detections,
                          avg_confidence, avg_distance,
                          round(inference_time_ms, 2), round(fps, 2))
        frame_id += 1

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    logger.close()
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

    

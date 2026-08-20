import csv
import os

class MetricsLogger:
    def __init__(self, filepath, model_name):
        self.filepath = filepath
        self.model_name = model_name

        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        file_exists = os.path.isfile(filepath)

        self.file = open(filepath, mode='a', newline='')
        self.writer = csv.writer(self.file)

        if not file_exists:
            self.writer.writerow([
                "model", "frame_id", "timestamp", "num_detections",
                "avg_confidence", "avg_distance_m", "inference_time_ms", "fps"
            ])

    def log_frame(self, frame_id, timestamp, num_detections, avg_confidence, avg_distance_m, inference_time_ms, fps):
        self.writer.writerow([
            self.model_name, frame_id, round(timestamp, 3), num_detections,
            avg_confidence, avg_distance_m, inference_time_ms, fps
        ])
        self.file.flush()  # scrive subito su disco, utile se il programma si interrompe

    def close(self):
        self.file.close()
# AI Detection — Domenico

Human detection e stima distanza. Pubblica su `percezione/detection`
(vedi [`../docs/interface_contract.md`](../docs/interface_contract.md)).

## Da fare

- [ ] Confronto modelli: YOLO / RT-DETR / NVIDIA PeopleNet
- [ ] Prime metriche di detection su video/immagini di test
- [ ] Stima distanza (calibrazione monoculare / depth / routine built-in)
- [ ] Containerizzazione Docker (compatibile Jetson via TensorRT/ONNX)
- [ ] Publisher MQTT verso `percezione/detection`
- [ ] Metriche: precision, recall, F1, mAP, FPS, tempo di inferenza (media + p95),
      uso CPU/GPU/memoria, errore distanza (MAE, RMSE)

## Setup locale

```bash
python3 -m venv venv
source venv/bin/activate
pip install ultralytics opencv-python paho-mqtt
```

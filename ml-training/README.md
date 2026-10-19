# WP1 – AI Detection Model  
**Pothole Detection & Management – MVP Tunisia**

Sprint 1 (Foundations) – AI Detection Model  
Owner: Tharaa (co: Jasseur)

---

## Project Goal

This work package builds the **pothole detection model** that powers the whole system.

The model receives a photo (from the mobile app) and returns:
- Severity score (1–5)
- Confidence
- Bounding boxes of detected potholes
- Inference time

This output is consumed by:
- **WP3** (Core API) → stores the report and decides whether to generate a work sheet
- **WP2** (RAG Agent) → generates the official work sheet when score ≥ 3
- **WP4** (Mobile App) → shows status to the citizen

---

## Current model (v2, YOLO11s)

`models/pothole_model.onnx` is a YOLO11s detector trained for 100 epochs on a T4 GPU with
[`colab/train_pothole_yolo11s.ipynb`](colab/train_pothole_yolo11s.ipynb).

**Data:** RDD2022 pothole boxes (D40, 3,674 images from 6 countries, [figshare](https://figshare.com/articles/dataset/RDD2022_-_The_multi-national_Road_Damage_Dataset_released_through_CRDDC_2022/21431547))
+ 300 close-up pothole photos ([Roboflow "Potholes Detection", CC BY 4.0](https://universe.roboflow.com/project-ssayl/potholes-detection-d4rma))
+ 15% pothole-free road photos from RDD2022, so the model learns what a normal road looks like.
Split 70 / 15 / 15 into train / val / test. The confidence threshold is tuned on val; the numbers below are measured once on test.

| Held-out test set (686 images) | |
|---|---|
| mAP50 | **0.562** |
| mAP50-95 | 0.248 |
| Precision / Recall | 0.616 / 0.537 |
| F1 at the tuned threshold (0.28) | 0.573 |
| CPU time, end to end (8-core laptop) | ≈ 240 ms |

On the 32 real road photos in `backend/app/static/photos/_seed/` it finds 24 of 30 potholes and raises
no alarm on the 2 pothole-free photos (the Sprint 1 model: 9 of 30, and 2 false alarms).
Full numbers: [`models/test_metrics.json`](models/test_metrics.json).

`inference.py` letterboxes the photo exactly like Ultralytics does during training, reads the input
size from the model file, and keeps boxes with `CONF_THRESHOLD` (default 0.28) and IoU-based NMS.

If Colab disconnects mid-training, [`colab/resume_training.ipynb`](colab/resume_training.ipynb) continues from the last epoch.
[`colab/round2_800px.ipynb`](colab/round2_800px.ipynb) fine-tunes at 800 px and compares accuracy and CPU speed against this model.
Result (same test set, same Colab CPU): 800 px scored mAP50 0.496 vs 0.562 and ran 1.53× slower (386 vs 252 ms), so we kept 640 px.
OpenVINO was only ~10% faster than ONNX Runtime (226 vs 252 ms), not worth an extra dependency.

---

## What is delivered in Sprint 1

| Deliverable | Status | Location |
|-------------|--------|----------|
| Training pipeline (YOLOv8n, 1 epoch) | Done | `train.py` |
| ONNX model | Done | `models/pothole_model.onnx` |
| Exact inference contract | Done | `inference.py` |
| Severity scoring rule (1–5) | Done | `severity_scoring.py` |
| CPU timing test | Done | Average **71.4 ms** |
| Dataset (prepared + converted) | Done | `datasets/yolo_*` |

---

## Project Structure

```text
wp1-ai-model/
├── models/
│   └── pothole_model.onnx          ← final model for WP3
├── datasets/
│   ├── yolo_annotated_potholes/    ← converted dataset 1
│   └── yolo_rdd2022_pothole/       ← converted dataset 2
├── runs/detect/pothole_yolov8n_sprint1/
├── train.py
├── export_onnx.py
├── inference.py                    ← main interface for WP3
├── severity_scoring.py
├── timing_test.py
├── data.yaml
├── requirements.txt
└── README.md
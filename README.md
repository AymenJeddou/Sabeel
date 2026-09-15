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
# Pothole detection model

Finds potholes in a photo and grades them 1-5. Used in-process by the Core
API (`backend/app/vision_client.py`) for every report, for the AI check of
repair photos, and for driving-mode frames.

**Results, limits and plans: [`MODEL_REPORT.md`](MODEL_REPORT.md).**

| | |
|---|---|
| Model | YOLO11s, ONNX on CPU (`models/pothole_model.onnx`) |
| Test split (686 images) | mAP50 0.562 · precision 0.616 · recall 0.537 |
| Latency | ~114 ms end to end on an 8-core laptop, 232 ms on Colab's 2 vCPUs (target < 250 ms) |
| Threshold | 0.28 (tuned on val) |

## Interface (Section 4.3)

```python
from inference import infer
infer(image_bytes, source="manual") -> {
    "score": int | None,          # 1-5, None when nothing is detected
    "confidence": float | None,   # best box
    "boxes": [{"x", "y", "w", "h", "conf", "class"}],   # pixels of the original image
    "image_size": [w, h],
    "inference_ms": float,
}
```

`source` (`manual` | `web` | `driving_mode`) picks the severity bands
(`severity_scoring.py`): close-up photos and dashcam frames show the same
pothole at very different sizes.

## Retrain: three commands

```bash
pip install -r requirements.txt
python build_dataset.py --rdd /path/to/RDD2022 --out datasets/sabeel_v2   # + --extra datasets/feedback_vN
python train.py           # GPU; or colab/train_pothole_yolo11s.ipynb (cell 4 runs build_dataset.py)
python export_onnx.py     # -> models/pothole_model.onnx
```

Then measure and compare before replacing the shipped model:

```bash
python evaluate.py --data datasets/sabeel_v2/data.yaml     # test split: mAP + what the API would do
python timing_test.py                                      # latency + seed-photo check
```

Replace `models/pothole_model.onnx` only if test mAP50 improves and the seed
check doesn't get worse.

## Tools

| Script | Purpose |
|---|---|
| `build_dataset.py` | The one dataset pipeline (RDD2022 + close-ups + negatives, 70/15/15) |
| `train.py` · `export_onnx.py` | Train and export (same settings as the notebook) |
| `evaluate.py` | mAP on a split + found / false alarms at the production threshold |
| `timing_test.py` | Median / p90 latency, seed photos found and false alarms |
| `quantize.py` | INT8 static quantization (detection head optionally in float) |
| `error_analysis.py` | Exports false negatives / positives on val for tagging |
| `export_feedback_dataset.py` | Officer and citizen corrections → versioned YOLO dataset |
| `severity_check.py` | Severity rule vs human labels, suggested bands |
| `eval/` | Protocols for the Tunisian test set and the severity labels |

## History

Sprint 1 trained YOLOv8n for one epoch to prove the pipeline (71 ms, but it
missed most potholes and scored a cartoon house 5/5). Sprint 2 replaced it
with this YOLO11s model (#41). The old `convert_to_yolo.py` dropped
pothole-free images (the cause of false alarms on cracks and manholes) and
had no test split; `build_dataset.py` replaces it.

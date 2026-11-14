# Model report: pothole detector v2 (YOLO11s)

Status on 2026-11-07. Every number below was measured, and each one says
what it was measured on. Numbers that still need data the team has to
collect are marked **to do**.

## 1. What the model is

| | |
|---|---|
| Architecture | YOLO11s (Ultralytics), one class `pothole` |
| Input | 640 × 640, letterboxed exactly as in training (`inference.py`) |
| Training | 100 epochs on a Colab T4, `colab/train_pothole_yolo11s.ipynb` |
| Data | RDD2022 D40 potholes (3,674 images, 6 countries) + 300 close-up photos (Roboflow, CC BY 4.0) + 15 % pothole-free road images; split 70/15/15 (3,199 / 685 / 686), seed 42 (`build_dataset.py`) |
| Runtime | ONNX (opset 12), ONNX Runtime on CPU, in-process in the Core API |
| Threshold | 0.28, chosen on **val** (max F1); the API's detection gate uses the same value |

## 2. Accuracy on the held-out test split (686 images, never used for tuning)

From `models/test_metrics.json`:

| Metric | Value | Target (cahier §2.2) |
|---|---|---|
| mAP50 | **0.562** | ≥ 0.75 |
| mAP50-95 | 0.248 | – |
| Precision / recall | 0.616 / 0.537 | – |
| F1 at the 0.28 threshold | 0.573 | – |

**The 0.75 target is not met.** Why, and what is being done, in §6.

## 3. Real-world checks

**32 seed photos** (Wikimedia Commons: 30 potholes, mostly Latin America and
Morocco, plus a manhole and a crack), production path `inference.infer`:

| Model | Potholes found | False alarms | Median latency* |
|---|---|---|---|
| float (shipped) | 24 / 30 | 0 / 2 | 114 ms |
| INT8, detection head in float | 23 / 30 | 0 / 2 | 64-70 ms |
| INT8, fully quantized | 0 / 30 | 0 / 2 | 56 ms |

\* End to end (decode, letterbox, model, NMS), `timing_test.py`, Intel
laptop CPU, 8 logical cores, ONNX Runtime 1.31. Colab's 2 vCPUs measured
232 ms for the model alone. **Latency target (< 250 ms) met.**

**Tunisian test set: to do** (issue #44). The protocol and tools are ready
in `eval/README.md`; the 50-80 photos have to be taken by the team.

## 4. Speed: INT8 quantization (issue #43)

`quantize.py`: static QDQ INT8, per-channel weights, opset upgraded to 13
(needed for per-channel), calibrated through the production preprocessing.

- Fully quantized, the model finds nothing: the detection head (box
  regression and the final concat) does not survive INT8, as expected for YOLO.
- Keeping the head's 84 nodes in float: **1.6-1.8× faster** with the same
  seed-photo results (one fewer pothole found, no false alarm).

Decision rule from #43: ship only if test mAP50 ≥ 0.55, ≥ 23/30 seed
potholes with 0/2 false alarms, and ≥ 1.4× faster. Two of three are met; the
**test mAP50 is still to measure** because the 686 test images live in the
Drive cache. On Colab:

```bash
python quantize.py --calib /content/data/val/images --n 200 --keep-head-float
python evaluate.py --model models/pothole_model_int8.onnx --data /content/data.yaml
```

The local experiment was calibrated on the seed photos (the only images on
this machine), so it overlaps with the seed check. The production INT8 file
must be calibrated on val. Until then the API keeps the float model.
Switching is one setting: `MODEL_PATH=models/pothole_model_int8.onnx`.

Free wins already in place: the ONNX session loads at API startup (no
~0.5 s first-request penalty), and `ONNX_INTRA_OP_THREADS` sets the thread
count explicitly.

## 5. Severity rule v2 (issue #42)

Severity is a 2-D proxy, the relative area of the largest box (depth cannot
be measured from one photo). v1 used one set of bands tuned for dashcam
views and added +1 above 0.85 confidence, so close-up citizen photos almost
all scored 5. v2 (`severity_scoring.py`):

- separate bands per capture mode: close-up (`manual`, `web`) vs dashcam (`driving_mode`);
- no confidence bonus.

Distribution on the 24 detected seed photos:

| Score | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| v1 | 1 | 1 | 2 | 3 | **17 (71 %)** |
| v2 | 3 | 5 | 6 | 6 | 4 (17 %) |

The v2 close-up bands are provisional: they spread the scores but are not yet
checked against human judgment. **To do:** label 50-100 photos with the
rubric in `eval/README.md` and run `severity_check.py` (confusion matrix plus
suggested bands).

## 6. Closing the gap to 0.75 (issue #46)

Context: published YOLO results on RDD2022 report mAP50 ≈ 0.64-0.72 averaged
over four damage classes, and potholes are among the hardest (small in
dashcam views). The CRDDC 2022 winner used an ensemble that is far too slow
for a CPU API. **0.75 on RDD2022 potholes alone with one small CPU model may
not be reachable;** the honest target to report is the one measured on
Tunisian photos.

Already ruled out: more epochs (val mAP50 flat at about 0.557 for the last
epochs). 800 px was **not** properly tested (the fine-tune restarted at
lr0 = 0.01 and stopped at epoch 21).

Plan, in order, each step measured on the same test split:

1. **Error analysis** (`error_analysis.py --data … --split val`): export 100
   false negatives and 100 false positives with boxes drawn, tag them (small or
   far, water-filled, shadow, patch, cut off, label error).
2. If more than about 10 % are label errors, relabel the worst cases.
3. Add data: Tunisian photos not in the frozen test set, plus the feedback
   loop's hard negatives (`export_feedback_dataset.py`, then
   `build_dataset.py --extra datasets/feedback_vN`).
4. If "small or far" dominates: 800 px fine-tuned from `best.pt` with
   lr0 = 0.001, warmup 0, SGD, 40 epochs, paired with the INT8 model to stay
   under 250 ms.
5. YOLO11m only together with INT8.
6. Cheap boosts at the end: copy-paste augmentation, mixup 0.1, scale 0.7.

## 7. Feedback loop (issue #28)

Every human decision becomes a label in the Core API (`feedback_labels`): an
officer's "not a pothole", two citizens' "not a pothole", and every approved
work sheet (positive, the clearest photo only). Photos are already blurred
and EXIF-stripped at intake. `export_feedback_dataset.py` writes a versioned
YOLO folder (`datasets/feedback_vN`, never overwritten) with a manifest; the
positives' boxes are the model's own and are marked `needs_review`. The
false-positive rate (not_pothole / labelled) is shown in the dashboard's
analytics.

## 8. Reproduce

```bash
pip install -r requirements.txt
python build_dataset.py --rdd /path/to/RDD2022 --out datasets/sabeel_v2
python train.py                       # GPU; or the Colab notebook
python export_onnx.py
python evaluate.py --data datasets/sabeel_v2/data.yaml
python timing_test.py
```

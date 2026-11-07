# Evaluation sets that need people in the field

Two datasets can only be made by the team, with phones, in Tunisia. The tools
to score them are ready; the photos are not (they cannot be invented).

## 1. Tunisian test set `tunisia_v1/` (issue #44)

**Collect 50-80 photos** with at least 2 phones in at least 3 areas (city
centre, residential street, outer or rural road):

- 35-50 **with potholes**: small, medium, large; dry and wet; daylight and
  dusk; taken standing over them like a citizen, and some from 5-10 m away;
- 15-30 **without potholes** (hard negatives): patched asphalt, manhole
  covers, drain grates, cracks without a hole, puddles on flat road, tree or
  pole shadows, speed bumps, a clean road.

**Privacy first (Law 2004-63):** strip EXIF (`exiftool -all= *.jpg`), blur
faces and plates, no close-ups of homes, record only the city name.

**Annotate** in CVAT / Label Studio / Roboflow, export "YOLO 1.1", one class
`0 pothole`. Box the visible hole including its broken edge, not the patch
around it. Negatives get an empty `.txt`. A second person reviews every image.

**Store** images in `tunisia_v1/images/`, labels in `tunisia_v1/labels/`, one
row per photo in `tunisia_v1/MANIFEST.csv` (who took it, phone, city, date,
condition tags, negative type, licence). Images are git-ignored by
`ml-training/.gitignore` (keep them on Drive); labels and the manifest are
committed.

**Score it, never train or tune on it:**

```bash
python evaluate.py --data eval/tunisia_v1/data.yaml --out eval/tunisia_v1/results.json
```

Report mAP50, mAP50-95, precision, recall, potholes found / N and false
alarms / M (also per negative type) in `MODEL_REPORT.md`.

## 2. Human severity labels `severity_labels.csv` (issue #42)

Put 50-100 photos (the seed photos plus the Tunisian ones) in
`eval/severity_photos/` and fill one row each. Two people rate
independently, then agree on `human_severity_final`.

| Severity | Rubric |
|---|---|
| 1 | Surface crack or shallow hole < 20 cm, off the wheel path |
| 2 | Hole < 20 cm, or 20-50 cm but shallow (surface layer only) |
| 3 | 20-50 cm, reaches below the surface layer |
| 4 | > 50 cm, or 20-50 cm deep in the wheel path |
| 5 | > 50 cm and deep (base layer exposed), or any hole that can make a two-wheeler fall |

Then:

```bash
python severity_check.py
```

It prints the confusion matrix against the current rule and suggests new
close-up bands. A change to `severity_scoring.py` needs team sign-off: the
score drives deadlines, work sheets and priority.

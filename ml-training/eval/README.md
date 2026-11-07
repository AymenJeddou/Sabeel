# Evaluation sets that need human eyes

Two datasets need a person to check them. The photos can come from Mapillary
(no fieldwork) or from the team's phones; either way, a human reviews the
labels, because the model cannot grade itself.

## 1. Tunisian test set `tunisia_v1/` (issue #44)

### Route A, no fieldwork: Mapillary (recommended)

Mapillary has thousands of crowdsourced street photos of Tunisian roads
(CC BY-SA 4.0). Get a free developer token at mapillary.com (Developers ->
Register an application), then:

```bash
set MAPILLARY_TOKEN=MLY|...
python fetch_mapillary.py --per-area 300 --out eval/tunisia_v1
```

It scans 9 cities, keeps every photo where the model sees a pothole plus as
many random photos where it sees nothing, and writes the model's boxes as
pre-labels. **Review every image** in Roboflow or Label Studio (import images
+ YOLO labels): delete wrong boxes, draw missed potholes, keep negatives
empty. That review is about one or two hours of desk work, and it is what
makes it ground truth. Then score it with `evaluate.py` below. These are
mostly car-mounted photos, so they also measure the driving mode.

### Route B, phone photos

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

Put 50-100 photos (the seed photos plus the reviewed Tunisian ones, Mapillary
included) in `eval/severity_photos/` and fill one row each. Two people rate
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

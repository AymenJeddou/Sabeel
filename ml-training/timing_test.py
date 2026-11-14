"""CPU latency of the production inference path (decode + letterbox + model + NMS).

    python timing_test.py                       # the 32 seed photos
    python timing_test.py path/to/images        # any folder
    MODEL_PATH=models/pothole_model_int8.onnx python timing_test.py

Prints the median and p90 over every image after one warm-up call, plus how
many seed photos the model finds. Target (cahier §2.2): under 250 ms.
"""
import os
import platform
import statistics
import sys
import time
from pathlib import Path

from inference import infer

DEFAULT = Path(__file__).resolve().parent.parent / "backend" / "app" / "static" / "photos" / "_seed"


def main() -> None:
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    imgs = sorted(p for p in folder.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png"))
    if not imgs:
        raise SystemExit(f"No images in {folder}")
    infer(imgs[0].read_bytes())  # warm-up: loads the ONNX session

    times, found, false_alarms = [], 0, 0
    for p in imgs:
        data = p.read_bytes()
        t0 = time.perf_counter()
        r = infer(data)
        times.append((time.perf_counter() - t0) * 1000)
        found += r["score"] is not None and not p.name.startswith("fp_")
        false_alarms += r["score"] is not None and p.name.startswith("fp_")

    p90 = statistics.quantiles(times, n=10)[-1] if len(times) > 1 else times[0]
    print(f"model:   {os.getenv('MODEL_PATH', 'models/pothole_model.onnx')}")
    print(f"machine: {platform.processor() or platform.machine()} · {os.cpu_count()} logical CPUs")
    print(f"images:  {len(imgs)} from {folder}")
    print(f"median:  {statistics.median(times):.1f} ms   p90: {p90:.1f} ms   min/max: {min(times):.1f}/{max(times):.1f} ms")
    if folder == DEFAULT:
        fps = sum(1 for p in imgs if p.name.startswith("fp_"))
        print(f"seed photos: potholes found {found}/{len(imgs) - fps}, false alarms {false_alarms}/{fps}")


if __name__ == "__main__":
    main()

"""
Rough CPU timing test required by the Action Plan.
Share the average number with WP3 this week.
Target: under 250 ms on a normal CPU.
"""

import time
from pathlib import Path
from inference import infer

def main():
    # Use a real image from the validation set
    val_dir = Path("datasets/yolo_annotated_potholes/images/val")
    imgs = list(val_dir.glob("*.jpg")) + list(val_dir.glob("*.png"))
    if not imgs:
        print("No validation images found!")
        return

    image_bytes = imgs[0].read_bytes()
    print(f"Using test image: {imgs[0].name}")

    # Warm-up
    _ = infer(image_bytes)

    times = []
    for i in range(10):
        t0 = time.perf_counter()
        result = infer(image_bytes)
        elapsed = (time.perf_counter() - t0) * 1000
        times.append(elapsed)
        print(f"  Run {i+1}: {elapsed:.1f} ms | score={result['score']} | boxes={len(result['boxes'])}")

    avg = sum(times) / len(times)
    print("\n==============================")
    print(f"Average inference time (CPU): {avg:.1f} ms")
    print(f"Min / Max: {min(times):.1f} / {max(times):.1f} ms")
    print("==============================")
    print("→ Share this average with WP3 this week.")

if __name__ == "__main__":
    main()
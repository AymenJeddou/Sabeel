"""
Convert Pascal VOC XML annotations → YOLO format (.txt)
Works for both:
  - annotated_potholes
  - rdd2022_pothole
"""

from pathlib import Path
import xml.etree.ElementTree as ET
import shutil
from tqdm import tqdm
import random

# ====================== CONFIG ======================
PROJECT_ROOT = Path(__file__).resolve().parent

DATASETS = {
    "annotated_potholes": {
        "src": PROJECT_ROOT / "datasets" / "annotated_potholes",
        "dst": PROJECT_ROOT / "datasets" / "yolo_annotated_potholes",
        "class_name": "pothole",          # the name used in XML
    },
    "rdd2022_pothole": {
        "src": PROJECT_ROOT / "datasets" / "rdd2022_pothole",
        "dst": PROJECT_ROOT / "datasets" / "yolo_rdd2022_pothole",
        "class_name": "D40",              # or "pothole" – we will force to class 0
    },
}

TRAIN_RATIO = 0.8
SEED = 42
# ====================================================


def convert_bbox(size, box):
    """Convert VOC bbox (xmin, ymin, xmax, ymax) → YOLO (x_center, y_center, w, h) normalized"""
    dw = 1.0 / size[0]
    dh = 1.0 / size[1]
    x = (box[0] + box[2]) / 2.0
    y = (box[1] + box[3]) / 2.0
    w = box[2] - box[0]
    h = box[3] - box[1]
    return (x * dw, y * dh, w * dw, h * dh)


def process_dataset(name, config):
    src = config["src"]
    dst = config["dst"]
    target_class = config["class_name"]

    print(f"\n=== Processing {name} ===")
    print(f"Source: {src}")

    # Find all XML files
    xml_files = list(src.rglob("*.xml"))
    if not xml_files:
        print(f"  No XML files found in {src}")
        return

    print(f"  Found {len(xml_files)} XML files")

    # Prepare destination
    for split in ["train", "val"]:
        (dst / "images" / split).mkdir(parents=True, exist_ok=True)
        (dst / "labels" / split).mkdir(parents=True, exist_ok=True)

    # Shuffle and split
    random.seed(SEED)
    random.shuffle(xml_files)
    split_idx = int(len(xml_files) * TRAIN_RATIO)
    train_files = xml_files[:split_idx]
    val_files = xml_files[split_idx:]

    def convert_one(xml_path, split):
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            # Image size
            size = root.find("size")
            w = int(size.find("width").text)
            h = int(size.find("height").text)

            # Find corresponding image
            filename = root.find("filename").text
            # Try common locations
            possible_img = [
                xml_path.parent / filename,
                xml_path.parent.parent / "images" / filename,
                xml_path.parent / filename.replace(".xml", ".jpg"),
            ]
            img_path = None
            for p in possible_img:
                if p.exists():
                    img_path = p
                    break
            if img_path is None:
                # Search more broadly
                matches = list(src.rglob(filename))
                if matches:
                    img_path = matches[0]
                else:
                    return False

            # Collect boxes (force everything to class 0 = pothole)
            yolo_lines = []
            for obj in root.findall("object"):
                name = obj.find("name").text.strip()
                # Accept any name that looks like pothole / D40
                if name.lower() in ["pothole", "d40", "pot-hole"] or "pothole" in name.lower():
                    bnd = obj.find("bndbox")
                    box = (
                        float(bnd.find("xmin").text),
                        float(bnd.find("ymin").text),
                        float(bnd.find("xmax").text),
                        float(bnd.find("ymax").text),
                    )
                    bb = convert_bbox((w, h), box)
                    yolo_lines.append(f"0 {bb[0]:.6f} {bb[1]:.6f} {bb[2]:.6f} {bb[3]:.6f}")

            if not yolo_lines:
                return False  # no valid pothole boxes

            # Copy image + write label
            stem = img_path.stem
            shutil.copy2(img_path, dst / "images" / split / f"{stem}{img_path.suffix}")
            with open(dst / "labels" / split / f"{stem}.txt", "w") as f:
                f.write("\n".join(yolo_lines))
            return True

        except Exception as e:
            print(f"  Error on {xml_path.name}: {e}")
            return False

    # Convert
    print("  Converting train...")
    train_ok = sum(convert_one(f, "train") for f in tqdm(train_files))
    print("  Converting val...")
    val_ok = sum(convert_one(f, "val") for f in tqdm(val_files))

    print(f"  Done → train: {train_ok} | val: {val_ok}")
    print(f"  Output: {dst}")


if __name__ == "__main__":
    for name, cfg in DATASETS.items():
        process_dataset(name, cfg)

    print("\nAll conversions finished!")
    print("Next: create data.yaml and start training.")
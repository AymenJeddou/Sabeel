from ultralytics import YOLO
from pathlib import Path

def main():
    # Load the smallest pretrained model (YOLOv8n)
    model = YOLO("yolov8n.pt")          # will download automatically the first time

    # Sprint 1 goal = working pipeline, not accuracy → 1 epoch only
    results = model.train(
        data="data.yaml",
        epochs=1,                       # ← required for Sprint 1
        imgsz=640,
        batch=8,                        # reduce to 4 if you have low RAM / CPU only
        device="cpu",                   # change to 0 if you have a GPU
        name="pothole_yolov8n_sprint1",
        exist_ok=True,
        patience=5,
        save=True,
        plots=True,
        workers=4,
    )

    print("\nTraining finished!")
    print("Best weights:", results.save_dir / "weights" / "best.pt")
    print("You can now export to ONNX.")

if __name__ == "__main__":
    main()
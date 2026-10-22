from ultralytics import YOLO

# Same settings as colab/train_pothole_yolo11s.ipynb, which produced models/pothole_model.onnx.
# That notebook also builds the dataset (RDD2022 D40 + close-up photos + negatives, 70/15/15)
# and writes data.yaml; run it on a GPU, this script is for local reruns on that data.

def main():
    model = YOLO("yolo11s.pt")          # downloads automatically the first time
    results = model.train(
        data="data.yaml",
        epochs=100,
        imgsz=640,
        batch=-1,                       # auto batch for the GPU
        device=0,
        patience=25,
        cos_lr=True,
        close_mosaic=10,
        name="pothole_yolo11s",
        exist_ok=True,
    )
    print("Best weights:", results.save_dir / "weights" / "best.pt")
    print("Next: python export_onnx.py")

if __name__ == "__main__":
    main()

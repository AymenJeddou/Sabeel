from ultralytics import YOLO
from pathlib import Path
import shutil

# Path to the best weights from training
weights = Path("runs/detect/pothole_yolov8n_sprint1/weights/best.pt")

print("Loading model...")
model = YOLO(str(weights))

print("Exporting to ONNX...")
onnx_path = model.export(
    format="onnx",
    imgsz=640,
    simplify=True,
    opset=12,
    dynamic=False,          # fixed shape is safer for WP3
)

print("ONNX exported to:", onnx_path)

# Copy it to a clean location that matches the shared config
models_dir = Path("models")
models_dir.mkdir(exist_ok=True)
final_path = models_dir / "pothole_model.onnx"
shutil.copy2(onnx_path, final_path)

print(f"\nFinal model ready at: {final_path.resolve()}")
print("This is the path you will put in MODEL_PATH for WP3.")
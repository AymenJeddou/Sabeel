"""INT8 static quantization of the ONNX detector (issue #43).

    python quantize.py --calib datasets/sabeel_v2/val/images --n 200
    python quantize.py --calib ../backend/app/static/photos/_seed --keep-head-float

Writes models/pothole_model_int8.onnx (QDQ format, per-channel weights). The
calibration images must come from the **val** split, never test. Then:

    MODEL_PATH=models/pothole_model_int8.onnx python timing_test.py      # speed + seed check
    python evaluate.py --model models/pothole_model_int8.onnx --data datasets/sabeel_v2/data.yaml   # mAP on test

Ship it (set MODEL_PATH) only if all three hold (decision rule of #43):
test mAP50 >= 0.55, >= 23/30 seed potholes found with 0/2 false alarms, and
end-to-end median >= 1.4x faster than the float model on the target machine.
"""
from __future__ import annotations

import argparse
import random
from pathlib import Path

import onnx
from onnxruntime.quantization import CalibrationDataReader, QuantFormat, QuantType, quantize_static
from onnxruntime.quantization.shape_inference import quant_pre_process

import inference

HERE = Path(__file__).resolve().parent


class Letterboxed(CalibrationDataReader):
    """Feeds calibration images through the exact production preprocessing."""

    def __init__(self, paths: list[Path], input_name: str, imgsz: int):
        self._it = iter(paths)
        self._name, self._imgsz = input_name, imgsz

    def get_next(self):
        for p in self._it:
            try:
                tensor, *_ = inference._preprocess(p.read_bytes(), self._imgsz)
                return {self._name: tensor}
            except ValueError:
                continue
        return None


def head_nodes(model_path: Path) -> list[str]:
    """Nodes of the detection head (last module), usually the most sensitive to INT8."""
    graph = onnx.load(str(model_path)).graph
    ids = [int(n.name.split("/")[1].split(".")[1]) for n in graph.node if n.name.startswith("/model.")]
    return [n.name for n in graph.node if n.name.startswith(f"/model.{max(ids)}/")]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--model", type=Path, default=HERE / "models" / "pothole_model.onnx")
    ap.add_argument("--out", type=Path, default=HERE / "models" / "pothole_model_int8.onnx")
    ap.add_argument("--calib", type=Path, required=True, help="folder of VAL images")
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--keep-head-float", action="store_true", help="leave the detection head in float")
    a = ap.parse_args()

    paths = sorted(p for p in a.calib.rglob("*") if p.suffix.lower() in (".jpg", ".jpeg", ".png"))
    random.Random(0).shuffle(paths)
    paths = paths[: a.n]
    print(f"calibrating on {len(paths)} images from {a.calib}")

    session, input_name, imgsz = inference._get_session()
    # Per-channel DequantizeLinear needs opset >= 13; the export is opset 12.
    from onnx import version_converter

    opset13 = a.out.with_suffix(".op13.onnx")
    onnx.save(version_converter.convert_version(onnx.load(str(a.model)), 13), str(opset13))
    prepped = a.out.with_suffix(".prep.onnx")
    quant_pre_process(str(opset13), str(prepped))
    opset13.unlink(missing_ok=True)
    exclude = head_nodes(prepped) if a.keep_head_float else []
    quantize_static(
        str(prepped),
        str(a.out),
        Letterboxed(paths, input_name, imgsz),
        quant_format=QuantFormat.QDQ,
        per_channel=True,
        weight_type=QuantType.QInt8,
        activation_type=QuantType.QUInt8,
        nodes_to_exclude=exclude,
    )
    prepped.unlink(missing_ok=True)
    print(f"wrote {a.out} ({a.out.stat().st_size / 1e6:.1f} MB, float: {a.model.stat().st_size / 1e6:.1f} MB)"
          + (f", {len(exclude)} head nodes kept in float" if exclude else ""))


if __name__ == "__main__":
    main()

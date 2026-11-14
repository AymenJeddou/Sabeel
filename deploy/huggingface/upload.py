"""Uploads Sabeel to a Hugging Face Space from your PC (same layout as the
deploy-hf.yml workflow).

    pip install huggingface_hub && huggingface-cli login
    python deploy/huggingface/upload.py <your-hf-name>/sabeel
"""
import shutil
import sys
import tempfile
from pathlib import Path

from huggingface_hub import HfApi

ROOT = Path(__file__).resolve().parents[2]
SKIP = shutil.ignore_patterns("node_modules", "dist", "chroma_db", ".env", "__pycache__", "tests", ".venv", "*.pyc")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    with tempfile.TemporaryDirectory() as tmp:
        space = Path(tmp)
        for folder in ("backend", "dashboard", "rag-service", "deploy"):
            shutil.copytree(ROOT / folder, space / folder, ignore=SKIP)
        ml = space / "ml-training"
        ml.mkdir()
        for f in ("inference.py", "severity_scoring.py"):
            shutil.copy(ROOT / "ml-training" / f, ml / f)
        shutil.copytree(ROOT / "ml-training" / "models", ml / "models")
        # Uploaded photos stay out; the seed photos are part of the demo.
        photos = space / "backend" / "app" / "static" / "photos"
        for p in photos.iterdir():
            if p.name != "_seed":
                shutil.rmtree(p) if p.is_dir() else p.unlink()
        shutil.copy(ROOT / "deploy" / "huggingface" / "Dockerfile", space / "Dockerfile")
        shutil.copy(ROOT / "deploy" / "huggingface" / "README.md", space / "README.md")
        HfApi().upload_folder(folder_path=str(space), repo_id=sys.argv[1], repo_type="space",
                              commit_message="Deploy from local", delete_patterns=["*"])
    print(f"Uploaded. The Space builds in ~10 min: https://huggingface.co/spaces/{sys.argv[1]}")


if __name__ == "__main__":
    main()

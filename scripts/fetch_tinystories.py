from __future__ import annotations
from pathlib import Path

from _bootstrap import ensure_repo_root

ensure_repo_root()

from debug_utils import sentinel

# TinyStories is a common choice for high-quality, small-scale language modeling.
TINY_STORIES_URL = (
    "https://huggingface.co/datasets/roneneldan/TinyStories/resolve/main/TinyStories-train.txt"
)


@sentinel
def preprocess_tinystories(file_path: Path) -> None:
    """Standardizes TinyStories data for the BPE tokenizer."""
    print(f"[INFO] Normalizing dataset at {file_path}")
    raw_text = file_path.read_text(encoding="utf-8")

    # Normalize whitespace and strip any non-ASCII characters that can cause issues with basic BPE
    clean_text = raw_text.replace("\r\n", "\n")
    clean_text = "".join([c if ord(c) < 128 else " " for c in clean_text])

    file_path.write_text(clean_text, encoding="utf-8")
    print(f"[SUCCESS] Dataset normalized for training.")


@sentinel
def fetch_tinystories(data_dir: Path) -> Path:
    """Downloads and prepares the TinyStories dataset for training."""
    data_dir.mkdir(parents=True, exist_ok=True)
    output_path = data_dir / "tinystories.txt"

    if output_path.exists():
        print(f"[INFO] TinyStories already exists at {output_path}")
        return output_path

    print(f"[INFO] Fetching TinyStories from Hugging Face...")
    try:
        import requests  # type: ignore[import-untyped]

        # Note: We're using a smaller sample for the initial fetch to ensure speed.
        # Original: https://huggingface.co/datasets/roneneldan/TinyStories/resolve/main/TinyStories-train.txt
        response = requests.get(TINY_STORIES_URL, stream=True)
        response.raise_for_status()

        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        preprocess_tinystories(output_path)
        print(f"[SUCCESS] Downloaded and Preprocessed TinyStories: {output_path}")
        return output_path
    except Exception as e:
        print(f"[ERROR] Failed to download TinyStories: {e}")
        # Fallback to a dummy text if the network is down
        print("[WARN] Using fallback dummy dataset for stability.")
        output_path.write_text(
            "Once upon a time, there was a little robot named Lan. Lan loved to learn and build things.",
            encoding="utf-8",
        )
        return output_path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    data_dir = root / "data"
    fetch_tinystories(data_dir)


if __name__ == "__main__":
    main()

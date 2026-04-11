from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from _bootstrap import ensure_repo_root

ensure_repo_root()


ROOT = Path(__file__).resolve().parents[1]
TEMP_DOWNLOADS = ROOT / "temp" / "downloads"
MODEL_CACHE_DIR = TEMP_DOWNLOADS / "models"

PHASE_PACKAGE_GROUPS: dict[str, list[str]] = {
    "phase4": [
        "playwright==1.58.0",
        "tavily-python==0.7.23",
        "mss==10.1.0",
        "pytesseract==0.3.13",
        "Pillow==12.2.0",
        "vosk==0.3.45",
        "pyttsx3==2.90",
        "PyAudio==0.2.14",
        "chromadb==0.5.23",
    ],
    "phase45": ["opencv-python", "easyocr", "ultralytics", "llama-cpp-python"],
    "phase5": ["datasets", "peft", "trl", "qdrant-client", "ray"],
}


@dataclass(frozen=True)
class HttpAsset:
    name: str
    url: str
    path: Path


HTTP_ASSETS: list[HttpAsset] = [
    HttpAsset(
        name="tinystories_text",
        url="https://huggingface.co/datasets/roneneldan/TinyStories/resolve/main/TinyStories-train.txt",
        path=MODEL_CACHE_DIR / "TinyStories-train.txt",
    ),
    HttpAsset(
        name="vosk_small_en",
        url="https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip",
        path=MODEL_CACHE_DIR / "vosk-model-small-en-us-0.15.zip",
    ),
    HttpAsset(
        name="tinyllama_q2k",
        url=(
            "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/"
            "tinyllama-1.1b-chat-v1.0.Q2_K.gguf"
        ),
        path=MODEL_CACHE_DIR / "tinyllama-1.1b-chat-v1.0.Q2_K.gguf",
    ),
]


def _run_pip_download(packages: Iterable[str], destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "-m",
        "pip",
        "download",
        "--dest",
        str(destination),
        "--retries",
        "10",
        "--timeout",
        "120",
        "--progress-bar",
        "off",
        *list(packages),
    ]
    print(f"[INFO] pip cache -> {destination}")
    subprocess.run(cmd, cwd=str(ROOT), check=True)


def _download_http_with_resume(asset: HttpAsset, retries: int = 5) -> None:
    asset.path.parent.mkdir(parents=True, exist_ok=True)

    import requests  # type: ignore[import-untyped]

    for attempt in range(1, retries + 1):
        existing_size = asset.path.stat().st_size if asset.path.exists() else 0
        headers: dict[str, str] = {}
        mode = "wb"
        if existing_size > 0:
            headers["Range"] = f"bytes={existing_size}-"
            mode = "ab"

        try:
            with requests.get(asset.url, stream=True, timeout=(15, 120), headers=headers) as response:
                if response.status_code == 416:
                    print(f"[INFO] {asset.name}: already complete ({asset.path})")
                    return
                if existing_size > 0 and response.status_code not in {206, 200}:
                    existing_size = 0
                    mode = "wb"
                response.raise_for_status()

                total = response.headers.get("Content-Length")
                total_text = f"+{total} bytes" if total else "unknown size"
                print(
                    f"[INFO] {asset.name}: attempt {attempt}/{retries}, writing {mode}, {total_text}"
                )

                with asset.path.open(mode) as file_handle:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            file_handle.write(chunk)
            print(f"[SUCCESS] {asset.name}: {asset.path}")
            return
        except Exception as exc:
            print(f"[WARN] {asset.name}: attempt {attempt} failed: {exc}")
            if attempt == retries:
                raise
            time.sleep(min(2 * attempt, 8))


def _sync_cached_assets_to_runtime_locations() -> None:
    dataset_src = MODEL_CACHE_DIR / "TinyStories-train.txt"
    dataset_dest = ROOT / "data" / "tinystories.txt"
    if dataset_src.exists() and not dataset_dest.exists():
        dataset_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dataset_src, dataset_dest)
        print(f"[INFO] copied dataset cache to {dataset_dest}")

    vosk_src = MODEL_CACHE_DIR / "vosk-model-small-en-us-0.15.zip"
    vosk_dest = ROOT / "models" / "downloads" / "vosk-model-small-en-us-0.15.zip"
    if vosk_src.exists() and not vosk_dest.exists():
        vosk_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(vosk_src, vosk_dest)
        print(f"[INFO] copied Vosk archive cache to {vosk_dest}")

    gguf_src = MODEL_CACHE_DIR / "tinyllama-1.1b-chat-v1.0.Q2_K.gguf"
    gguf_dest = ROOT / "models" / "downloads" / "tinyllama-1.1b-chat-v1.0.Q2_K.gguf"
    if gguf_src.exists() and not gguf_dest.exists():
        gguf_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(gguf_src, gguf_dest)
        print(f"[INFO] copied GGUF cache to {gguf_dest}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prefetch package/model assets into temp/downloads for low-speed internet workflows."
    )
    parser.add_argument(
        "--phase",
        action="append",
        choices=["phase4", "phase45", "phase5"],
        help="Specific package cache group(s) to prefetch. Repeatable.",
    )
    parser.add_argument(
        "--all-phases",
        action="store_true",
        help="Prefetch all package cache groups.",
    )
    parser.add_argument(
        "--skip-packages",
        action="store_true",
        help="Skip pip package downloads and only run requested HTTP/runtime sync steps.",
    )
    parser.add_argument(
        "--with-model-assets",
        action="store_true",
        help="Prefetch resumable HTTP model/data assets into temp/downloads/models.",
    )
    parser.add_argument(
        "--asset",
        action="append",
        choices=[asset.name for asset in HTTP_ASSETS],
        help="Specific HTTP asset name(s) to prefetch. Repeatable; defaults to all assets.",
    )
    parser.add_argument(
        "--sync-runtime-paths",
        action="store_true",
        help="Copy cached model/data assets into their runtime paths if missing.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.skip_packages:
        selected_phases = set(args.phase or [])
        if args.all_phases or not selected_phases:
            selected_phases = set(PHASE_PACKAGE_GROUPS.keys())

        for phase in sorted(selected_phases):
            packages = PHASE_PACKAGE_GROUPS[phase]
            destination = TEMP_DOWNLOADS / phase
            _run_pip_download(packages, destination)

    if args.with_model_assets:
        selected_asset_names = set(args.asset or [])
        selected_assets = [
            asset for asset in HTTP_ASSETS if not selected_asset_names or asset.name in selected_asset_names
        ]
        for asset in selected_assets:
            _download_http_with_resume(asset)

    if args.sync_runtime_paths:
        _sync_cached_assets_to_runtime_locations()

    print("[SUCCESS] prefetch complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

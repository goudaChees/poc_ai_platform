from __future__ import annotations

import os
from contextlib import asynccontextmanager
from importlib.metadata import version
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

import cv2
import paddle
from fastapi import (
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from paddleocr import PaddleOCR


SCHEMA_VERSION = "1.0"
ENGINE_KEY = "paddle"
DISPLAY_NAME = "PaddleOCR"
RUNTIME_VERSION = "1.1.0"

MODEL_ROOT = Path(
    os.getenv(
        "PADDLE_MODEL_ROOT",
        "/opt/ocr/models",
    )
)

SUPPORTED_LANG = "korean"

_engine: PaddleOCR | None = None


def get_engine_version() -> str:
    return version(
        "paddleocr"
    )


def get_gpu_available() -> bool:
    try:
        return (
            paddle.device.cuda.device_count()
            > 0
        )
    except Exception:
        return False


def get_device() -> str:
    if get_gpu_available():
        return "GPU"

    return "CPU"


def build_ocr_engine() -> PaddleOCR:
    model_dirs = {
        "doc_orientation_classify_model_dir":
            MODEL_ROOT / "PP-LCNet_x1_0_doc_ori",

        "doc_unwarping_model_dir":
            MODEL_ROOT / "UVDoc",

        "text_detection_model_dir":
            MODEL_ROOT / "PP-OCRv5_server_det",

        "textline_orientation_model_dir":
            MODEL_ROOT / "PP-LCNet_x1_0_textline_ori",

        "text_recognition_model_dir":
            MODEL_ROOT / "korean_PP-OCRv5_mobile_rec",
    }

    missing_models = [
        str(path)
        for path in model_dirs.values()
        if not path.is_dir()
    ]

    if missing_models:
        raise RuntimeError(
            "Paddle OCR 모델 디렉터리가 없습니다: "
            + ", ".join(
                missing_models
            )
        )

    print(
        "==== LOAD OFFLINE PADDLE OCR MODEL ====",
        flush=True,
    )

    engine = PaddleOCR(
        doc_orientation_classify_model_name=(
            "PP-LCNet_x1_0_doc_ori"
        ),
        doc_orientation_classify_model_dir=str(
            MODEL_ROOT
            / "PP-LCNet_x1_0_doc_ori"
        ),

        doc_unwarping_model_name="UVDoc",
        doc_unwarping_model_dir=str(
            MODEL_ROOT
            / "UVDoc"
        ),

        text_detection_model_name=(
            "PP-OCRv5_server_det"
        ),
        text_detection_model_dir=str(
            MODEL_ROOT
            / "PP-OCRv5_server_det"
        ),

        textline_orientation_model_name=(
            "PP-LCNet_x1_0_textline_ori"
        ),
        textline_orientation_model_dir=str(
            MODEL_ROOT
            / "PP-LCNet_x1_0_textline_ori"
        ),

        text_recognition_model_name=(
            "korean_PP-OCRv5_mobile_rec"
        ),
        text_recognition_model_dir=str(
            MODEL_ROOT
            / "korean_PP-OCRv5_mobile_rec"
        ),
    )

    print(
        "==== OFFLINE PADDLE OCR READY ====",
        flush=True,
    )

    return engine


def build_blocks(
    ocr_data: Any,
) -> list[dict[str, object]]:
    raw_texts = list(
        ocr_data.get(
            "rec_texts",
            [],
        )
    )

    raw_scores = list(
        ocr_data.get(
            "rec_scores",
            [],
        )
    )

    raw_boxes = list(
        ocr_data.get(
            "rec_boxes",
            [],
        )
    )

    if not (
        len(raw_texts)
        == len(raw_scores)
        == len(raw_boxes)
    ):
        raise RuntimeError(
            "PaddleOCR 결과 길이가 "
            "일치하지 않습니다: "
            f"texts={len(raw_texts)}, "
            f"scores={len(raw_scores)}, "
            f"boxes={len(raw_boxes)}"
        )

    blocks: list[
        dict[str, object]
    ] = []

    for (
        raw_text,
        raw_score,
        raw_box,
    ) in zip(
        raw_texts,
        raw_scores,
        raw_boxes,
        strict=True,
    ):
        text = str(
            raw_text
        ).strip()

        if not text:
            continue

        bbox = [
            int(value)
            for value in list(
                raw_box
            )
        ]

        if len(bbox) != 4:
            raise RuntimeError(
                "PaddleOCR bbox 형식이 "
                "올바르지 않습니다: "
                f"{bbox}"
            )

        blocks.append(
            {
                "index": len(
                    blocks
                ),
                "text": text,
                "confidence": float(
                    raw_score
                ),
                "bbox": bbox,
                "page": 1,
            }
        )

    return blocks


@asynccontextmanager
async def lifespan(
    app: FastAPI,
):
    global _engine

    _engine = build_ocr_engine()

    yield

    _engine = None


app = FastAPI(
    title="OCR Paddle Service",
    version=RUNTIME_VERSION,
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict[str, object]:
    if _engine is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "OCR engine is not ready."
            ),
        )

    return {
        "status": "READY",
        "engine_key": ENGINE_KEY,
        "version": (
            get_engine_version()
        ),
        "device": get_device(),
        "gpu_available": (
            get_gpu_available()
        ),
    }


@app.get("/metadata")
def metadata() -> dict[str, object]:
    return {
        "schema_version": (
            SCHEMA_VERSION
        ),
        "engine_key": ENGINE_KEY,
        "display_name": DISPLAY_NAME,
        "version": (
            get_engine_version()
        ),
        "runtime_version": (
            RUNTIME_VERSION
        ),
        "runtime_type": "HTTP_API",
        "device": get_device(),
        "gpu_available": (
            get_gpu_available()
        ),
        "languages": [
            SUPPORTED_LANG,
        ],
        "api": {
            "health": "/health",
            "metadata": "/metadata",
            "ocr": "/ocr",
        },
    }


@app.post("/ocr")
async def recognize(
    file: UploadFile = File(...),
    lang: str = Form(
        SUPPORTED_LANG
    ),
) -> dict[str, object]:
    if _engine is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "OCR engine is not ready."
            ),
        )

    normalized_lang = (
        lang
        .strip()
        .lower()
    )

    if (
        normalized_lang
        != SUPPORTED_LANG
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "현재 ocr-paddle 이미지에서 "
                "지원하는 lang은 "
                f"{SUPPORTED_LANG}입니다."
            ),
        )

    filename = (
        file.filename
        or "image"
    )

    suffix = (
        Path(filename).suffix
        or ".img"
    )

    temporary_path: (
        str
        | None
    ) = None

    try:
        with NamedTemporaryFile(
            suffix=suffix,
            delete=False,
        ) as temporary_file:
            temporary_path = (
                temporary_file.name
            )

            while True:
                chunk = await file.read(
                    1024 * 1024
                )

                if not chunk:
                    break

                temporary_file.write(
                    chunk
                )

        image = cv2.imread(
            temporary_path
        )

        if image is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    "이미지 파일을 "
                    "읽을 수 없습니다."
                ),
            )

        height, width = (
            image.shape[:2]
        )

        print(
            "==============================",
            flush=True,
        )
        print(
            f"PADDLE OCR START: {filename}",
            flush=True,
        )
        print(
            "==============================",
            flush=True,
        )

        prediction = _engine.predict(
            temporary_path
        )

        if not prediction:
            raise HTTPException(
                status_code=500,
                detail=(
                    "PaddleOCR 결과가 "
                    "없습니다."
                ),
            )

        ocr_data = (
            prediction[0]
        )

        blocks = build_blocks(
            ocr_data
        )

        full_text = "\n".join(
            str(
                block["text"]
            )
            for block in blocks
        )

        print(
            f"PADDLE OCR END: {filename}",
            flush=True,
        )
        print(
            f"block_count: {len(blocks)}",
            flush=True,
        )

        return {
            "schema_version": (
                SCHEMA_VERSION
            ),
            "status": "SUCCESS",
            "engine_key": (
                ENGINE_KEY
            ),
            "version": (
                get_engine_version()
            ),
            "device": get_device(),
            "image": {
                "width": int(
                    width
                ),
                "height": int(
                    height
                ),
            },
            "text": full_text,
            "blocks": blocks,
        }

    except HTTPException:
        raise

    except Exception as exc:
        print(
            "==== PADDLE OCR ERROR ====",
            flush=True,
        )
        print(
            repr(exc),
            flush=True,
        )

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc

    finally:
        await file.close()

        if temporary_path:
            try:
                os.remove(
                    temporary_path
                )
            except FileNotFoundError:
                pass
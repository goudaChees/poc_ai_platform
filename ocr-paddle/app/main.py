from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import (
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from paddleocr import PaddleOCR


MODEL_ROOT = Path(
    os.getenv(
        "PADDLE_MODEL_ROOT",
        "/opt/ocr/models",
    )
)

SUPPORTED_LANG = "korean"

_engine: PaddleOCR | None = None


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
            + ", ".join(missing_models)
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
            MODEL_ROOT / "PP-LCNet_x1_0_doc_ori"
        ),

        doc_unwarping_model_name="UVDoc",
        doc_unwarping_model_dir=str(
            MODEL_ROOT / "UVDoc"
        ),

        text_detection_model_name=(
            "PP-OCRv5_server_det"
        ),
        text_detection_model_dir=str(
            MODEL_ROOT / "PP-OCRv5_server_det"
        ),

        textline_orientation_model_name=(
            "PP-LCNet_x1_0_textline_ori"
        ),
        textline_orientation_model_dir=str(
            MODEL_ROOT / "PP-LCNet_x1_0_textline_ori"
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
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict[str, str]:
    if _engine is None:
        raise HTTPException(
            status_code=503,
            detail="OCR engine is not ready.",
        )

    return {
        "status": "ok",
        "provider": "PADDLE",
    }


@app.post("/ocr")
async def recognize(
    file: UploadFile = File(...),
    lang: str = Form(SUPPORTED_LANG),
) -> dict[str, object]:
    if _engine is None:
        raise HTTPException(
            status_code=503,
            detail="OCR engine is not ready.",
        )

    normalized_lang = lang.strip().lower()

    if normalized_lang != SUPPORTED_LANG:
        raise HTTPException(
            status_code=400,
            detail=(
                "현재 ocr-paddle 이미지에서 "
                f"지원하는 lang은 {SUPPORTED_LANG}입니다."
            ),
        )

    filename = file.filename or "image"

    suffix = (
        Path(filename).suffix
        or ".img"
    )

    temporary_path: str | None = None

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
                    "PaddleOCR 결과가 없습니다."
                ),
            )

        ocr_data = prediction[0]

        raw_texts = ocr_data.get(
            "rec_texts",
            [],
        )

        texts = [
            str(text)
            for text in list(raw_texts)
            if str(text).strip()
        ]

        raw_scores = ocr_data.get(
            "rec_scores",
            [],
        )

        scores = [
            float(score)
            for score in list(
                raw_scores
            )
        ]

        print(
            f"PADDLE OCR END: {filename}",
            flush=True,
        )
        print(
            f"text_count: {len(texts)}",
            flush=True,
        )

        return {
            "provider": "PADDLE",
            "texts": texts,
            "scores": scores,
        }

    finally:
        await file.close()

        if temporary_path:
            try:
                os.remove(
                    temporary_path
                )
            except FileNotFoundError:
                pass
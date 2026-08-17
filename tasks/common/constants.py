from __future__ import annotations

import os

OCR_MEDIA_ROOT = os.getenv(
    "OCR_MEDIA_ROOT",
    "/opt/airflow/media",
)

OCR_FILES_ROOT = os.getenv(
    "OCR_FILES_ROOT",
    "/opt/airflow/ocrfiles",
)

OCR_RESULTS_ROOT = os.getenv(
    "OCR_RESULTS_ROOT",
    "/opt/airflow/ocrresults",
)

OCR_WORK_ROOT = os.getenv(
    "OCR_WORK_ROOT",
    "/opt/airflow/ocrwork",
)
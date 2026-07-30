from __future__ import annotations

import os
from typing import Any

import requests


BACKEND_API_BASE_URL = os.getenv("BACKEND_API_BASE_URL")


def update_pipeline_stage(
    pipeline_info: dict[str, Any],
    stage: str,
    airflow_run_id: str | None = None,
) -> dict[str, Any]:
    required_fields = {
        "document_id",
        "execution_id",
    }

    missing_fields = sorted(required_fields - set(pipeline_info.keys()))

    if missing_fields:
        raise ValueError(
            "Pipeline Stage 갱신 필수값이 없습니다: "
            + ", ".join(missing_fields)
        )

    if not BACKEND_API_BASE_URL:
        raise RuntimeError("BACKEND_API_BASE_URL 환경변수가 없습니다.")

    payload = {
        "document_id": int(pipeline_info["document_id"]),
        "execution_id": int(pipeline_info["execution_id"]),
        "stage": stage,
        "airflow_run_id": airflow_run_id,
    }

    print("==== PIPELINE STAGE UPDATE START ====", flush=True)
    print(payload, flush=True,)

    response = requests.post(
        (
            f"{BACKEND_API_BASE_URL}"
            "/api/ocr/internal/pipeline/stage/"
        ),
        json=payload,
        timeout=30,
    )

    print(f"status: {response.status_code}", flush=True)
    print(f"body: {response.text}", flush=True)

    response.raise_for_status()

    result = response.json()

    if not isinstance(result, dict):
        raise ValueError(
            "Pipeline Stage API 응답은 "
            "JSON 객체여야 합니다."
        )

    print("==== PIPELINE STAGE UPDATE SUCCESS ====", flush=True)

    return result
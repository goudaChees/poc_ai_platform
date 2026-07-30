from __future__ import annotations

import os
from typing import Any

import requests
from dotenv import load_dotenv


load_dotenv()


BACKEND_API_BASE_URL = os.getenv(
    "BACKEND_API_BASE_URL"
)


def complete_pipeline(
    validation_info: dict[str, Any],
    airflow_run_id: str,
) -> dict[str, Any]:
    required_fields = {
        "document_id",
        "execution_id",
        "validation_status",
    }

    missing_fields = sorted(
        required_fields
        - set(validation_info.keys())
    )

    if missing_fields:
        raise ValueError(
            "Pipeline 완료 처리 필수 값이 없습니다: "
            + ", ".join(missing_fields)
        )

    validation_status = str(
        validation_info["validation_status"]
    )

    if validation_status != "SUCCESS":
        raise ValueError(
            "RAG 검증이 성공하지 않았습니다: "
            f"{validation_status}"
        )

    if not BACKEND_API_BASE_URL:
        raise RuntimeError(
            "BACKEND_API_BASE_URL "
            "환경변수가 없습니다."
        )

    payload = {
        "document_id": int(
            validation_info["document_id"]
        ),
        "execution_id": int(
            validation_info["execution_id"]
        ),
        "airflow_run_id": airflow_run_id,
        "validation_status": validation_status,
    }

    print(
        "==== PIPELINE COMPLETE API START ====",
        flush=True,
    )
    print(
        payload,
        flush=True,
    )

    response = requests.post(
        (
            f"{BACKEND_API_BASE_URL}"
            "/api/ocr/internal/pipeline/complete/"
        ),
        json=payload,
        timeout=30,
    )

    print(
        f"STATUS: {response.status_code}",
        flush=True,
    )
    print(
        f"BODY: {response.text}",
        flush=True,
    )

    response.raise_for_status()

    response_data = response.json()

    if not isinstance(
        response_data,
        dict,
    ):
        raise ValueError(
            "Pipeline 완료 API 응답은 "
            "JSON 객체여야 합니다."
        )

    result = dict(
        validation_info
    )

    result.update(
        {
            "pipeline_status": (
                response_data.get("status")
            ),
            "current_stage": (
                response_data.get(
                    "current_stage"
                )
            ),
            "airflow_run_id": airflow_run_id,
        }
    )

    print("==== PIPELINE COMPLETE API SUCCESS ====", flush=True,)
    print(result, flush=True,)

    return result
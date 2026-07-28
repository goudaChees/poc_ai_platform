import os

import requests
from dotenv import load_dotenv

load_dotenv()

BACKEND_API_BASE_URL = os.getenv(
    "BACKEND_API_BASE_URL"
)

TASK_STAGE_MAP = {
    "check_file": "FILE_PREPARATION",
    "prepare_image": "DOCUMENT_CONVERSION",
    "run_ocr": "OCR",
    "save_result": "OCR",
    "chunking": "CHUNKING",
    "embedding": "EMBEDDING",
}

def notify_pipeline_failed(context):
    dag_run = context.get("dag_run")

    task_instance = (
        context.get("task_instance")
        or context.get("ti")
    )

    if dag_run is None:
        print(
            "==== PIPELINE FAILURE CALLBACK SKIP ====",
            flush=True,
        )
        print(
            "dag_run이 없습니다.",
            flush=True,
        )
        return

    conf = dag_run.conf or {}

    document_id = conf.get(
        "document_id"
    )

    execution_id = conf.get(
        "execution_id"
    )

    if document_id is None or execution_id is None:
        print(
            "==== PIPELINE FAILURE CALLBACK SKIP ====",
            flush=True,
        )
        print(
            f"document_id: {document_id}",
            flush=True,
        )
        print(
            f"execution_id: {execution_id}",
            flush=True,
        )
        return

    task_id = (
        task_instance.task_id
        if task_instance is not None
        else "unknown"
    )

    stage = TASK_STAGE_MAP.get(
        task_id,
        "OCR",
    )

    exception = context.get(
        "exception"
    )

    error_message = (
        repr(exception)
        if exception is not None
        else "Airflow Task failed"
    )

    if not BACKEND_API_BASE_URL:
        raise RuntimeError(
            "BACKEND_API_BASE_URL 환경변수가 없습니다."
        )

    payload = {
        "document_id": document_id,
        "execution_id": execution_id,
        "airflow_run_id": dag_run.run_id,
        "task_id": task_id,
        "stage": stage,
        "error_message": error_message,
    }

    print(
        "==== PIPELINE FAILURE CALLBACK START ====",
        flush=True,
    )
    print(
        payload,
        flush=True,
    )

    response = requests.post(
        (
            f"{BACKEND_API_BASE_URL}"
            "/api/ocr/internal/pipeline/fail/"
        ),
        json=payload,
        timeout=10,
    )

    print(
        f"FAIL CALLBACK STATUS: "
        f"{response.status_code}",
        flush=True,
    )
    print(
        f"FAIL CALLBACK BODY: "
        f"{response.text}",
        flush=True,
    )

    response.raise_for_status()
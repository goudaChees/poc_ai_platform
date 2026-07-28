import requests
from dotenv import load_dotenv
import os

load_dotenv()

BACKEND_API_BASE_URL = os.getenv("BACKEND_API_BASE_URL")

def save_result(ocr_info):
    if not BACKEND_API_BASE_URL:
        raise RuntimeError(
            "BACKEND_API_BASE_URL 환경변수가 없습니다."
        )

    response = requests.post(
        f"{BACKEND_API_BASE_URL}"
        "/api/ocr/internal/ocr/save_result/",
        json=ocr_info,
        timeout=30
    )

    print("STATUS:", response.status_code, flush=True)
    print("BODY:", response.text, flush=True)

    response.raise_for_status()

    response_data = response.json()

    if not isinstance(
        response_data,
        dict,
    ):
        raise ValueError(
            "save_result API 응답은 JSON 객체여야 합니다."
        )

    # API에서 반환한 result_id 등의 값을 유지하면서,
    # Chunking에 필요한 OCR 정보도 그대로 전달한다.
    saved_ocr_info = dict(
        response_data
    )

    saved_ocr_info.update(
        ocr_info
    )

    print("==== SAVE RESULT RETURN ====")
    print(f"saved_ocr_info: {saved_ocr_info}")

    return saved_ocr_info
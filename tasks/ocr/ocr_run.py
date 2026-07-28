import json
import os
from paddleocr import PaddleOCR
from tasks.common.constants import OCR_MEDIA_ROOT

ocr_engine = None

def get_ocr_engine():
    global ocr_engine

    if ocr_engine is None:

        print("==== LOAD PADDLE OCR MODEL ====")

        ocr_engine = PaddleOCR(
            lang="korean"
        )

        print("==== PADDLE OCR READY ====")

    return ocr_engine

def run_ocr(image_info):
    ocr = get_ocr_engine()

    document_id = image_info["document_id"]
    execution_id = image_info["execution_id"]
    image_files = image_info["image_files"]

    if not image_files:
        raise ValueError(
            "OCR을 실행할 이미지가 없습니다."
        )

    results = []


    for page_number, image_path in enumerate(
        image_files,
        start=1,
    ):
        if not os.path.isfile(image_path):
            raise FileNotFoundError(
                f"OCR 이미지 파일을 찾을 수 없습니다: {image_path}"
            )

        print("================================")
        print(f"OCR START: {image_path}")
        print(f"page_number: {page_number}")
        print(f"execution_id: {execution_id}")
        print("================================")

        prediction = ocr.predict(image_path)

        if not prediction:
            raise RuntimeError(
                f"PaddleOCR 결과가 없습니다: {image_path}"
            )

        ocr_data = prediction[0]

        texts = list(
            ocr_data.get("rec_texts", [])
        )

        scores = [
            float(score)
            for score in ocr_data.get("rec_scores", [])
        ]

        results.append(
            {
                "page_number": page_number,
                "image_path": image_path,
                "texts": texts,
                "scores": scores,
            }
        )

        print("==============================")
        print(f"OCR END: {image_path}")
        print(f"text_count: {len(texts)}")
        print("==============================")

    result_dir = os.path.join(
        OCR_MEDIA_ROOT,
        "ocr_results",
        str(document_id)
    )

    os.makedirs(
        result_dir,
        exist_ok=True
    )

    result_file = os.path.join(
        result_dir,
        "result.json"
    )

    result_relative_path = os.path.join(
        "ocr_results",
        str(document_id),
        "result.json"
    )

    result_payload = {
        "document_id": document_id,
        "execution_id": execution_id,
        "results": results,
    }


    with open(
        result_file,
        "w",
        encoding="utf-8"
    ) as result_json_file:

        json.dump(
            result_payload,
            result_json_file,
            ensure_ascii=False,
            indent=2,
        )

    print("==== OCR RESULT SAVED ====")
    print(f"document_id: {document_id}")
    print(f"execution_id: {execution_id}")
    print(f"result_file: {result_file}")
    print(f"result_relative_path: {result_relative_path}")

    return {
        "document_id": document_id,
        "execution_id": execution_id,
        "result_path": result_relative_path
    }
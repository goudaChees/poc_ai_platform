import os
import fitz
from tasks.common.constants import OCR_MEDIA_ROOT

SUPPORTED_IMAGE_TYPES = {
    "jpg",
    "jpeg",
    "png",
}

def prepare_image(file_info: dict[str, Any],) -> dict[str, Any]:
    required_fields = {
        "document_id",
        "execution_id",
        "file_path",
        "file_type",
    }

    missing_fields = sorted(
        required_fields
        - set(file_info.keys())
    )

    if missing_fields:
        raise ValueError(
            "문서 변환 필수 값이 없습니다: "
            + ", ".join(
                missing_fields
            )
        )

    file_type = str(file_info["file_type"]).strip().lower()

    if file_type == "pdf":
        return _convert_pdf(file_info)

    if file_type in (SUPPORTED_IMAGE_TYPES):
        return _prepare_single_image(file_info)

    raise ValueError(
        "지원하지 않는 파일 형식입니다: "
        f"{file_type}"
    )

def _convert_pdf(file_info: dict[str, Any],) -> dict[str, Any]:
    document_id = int(file_info["document_id"])

    execution_id = int(file_info["execution_id"])

    source_file_path = str(file_info["file_path"])

    if not os.path.isfile(source_file_path):
        raise FileNotFoundError(
            "PDF 파일을 찾을 수 없습니다: "
            f"{source_file_path}"
        )

    output_dir = os.path.join(
        OCR_MEDIA_ROOT,
        "ocr_images",
        str(
            document_id
        ),
    )

    os.makedirs(
        output_dir,
        exist_ok=True,
    )

    image_files: list[str] = []

    with fitz.open(
        source_file_path
    ) as pdf:
        for page_index in range(len(pdf)):
            page = pdf.load_page(page_index)

            pixmap = page.get_pixmap(dpi=300, alpha=False,)

            image_path = os.path.join(
                output_dir,
                (
                    "page_"
                    f"{page_index + 1:03d}"
                    ".png"
                ),
            )

            pixmap.save(image_path)

            image_files.append(image_path)

    if not image_files:
        raise ValueError(
            "PDF에서 변환된 페이지가 "
            "없습니다: "
            f"{source_file_path}"
        )

    print("==== PDF CONVERT SUCCESS ====",  flush=True,)
    print(f"document_id: {document_id}", flush=True,)
    print(f"execution_id: {execution_id}", flush=True,)
    print(f"page_count: {len(image_files)}", flush=True,)
    print(f"output_dir: {output_dir}", flush=True,)
    print("source_file_path: " f"{source_file_path}", flush=True,)

    return {
        "document_id": document_id,
        "execution_id": execution_id,
        "file_type": str(file_info["file_type"]),
        "source_file_path": source_file_path,
        "image_files": image_files,
    }


def _prepare_single_image(file_info: dict[str, Any],) -> dict[str, Any]:
    document_id = int(file_info["document_id"])

    execution_id = int(file_info["execution_id"])

    source_file_path = str(file_info["file_path"])

    if not os.path.isfile(source_file_path):
        raise FileNotFoundError(
            "이미지 파일을 찾을 수 없습니다: "
            f"{source_file_path}"
        )

    print("==== IMAGE PREPARE SUCCESS ====", flush=True,)
    print(f"document_id: {document_id}", flush=True,)
    print(f"execution_id: {execution_id}", flush=True,)
    print("image_path: " f"{source_file_path}", flush=True,)

    return {
        "document_id": document_id,
        "execution_id": execution_id,
        "file_type": str(file_info["file_type"]),
        "source_file_path": source_file_path,
        "image_files": [source_file_path],
    }
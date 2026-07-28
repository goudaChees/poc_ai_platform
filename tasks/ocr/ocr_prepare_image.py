import os
import fitz
from tasks.common.constants import OCR_MEDIA_ROOT

SUPPORTED_IMAGE_TYPES = {
    "jpg",
    "jpeg",
    "png",
}

def prepare_image(file_info):

    file_type = file_info["file_type"].lower()

    if file_type == "pdf":
        return _convert_pdf(file_info)

    elif file_type in SUPPORTED_IMAGE_TYPES:
        return _prepare_single_image(file_info)

    raise ValueError(f"지원하지 않는 파일 형식 : {file_type}")



def _convert_pdf(file_info):

    document_id = file_info["document_id"]
    execution_id = file_info["execution_id"]
    full_path = file_info["file_path"]

    output_dir = os.path.join(
        OCR_MEDIA_ROOT,
        "ocr_images",
        str(document_id)
    )

    os.makedirs(
        output_dir,
        exist_ok=True
    )

    image_files = []

    with fitz.open(full_path) as pdf:

        for page_index in range(len(pdf)):
            page = pdf.load_page(page_index)

            pixmap = page.get_pixmap(
                dpi=300,
                alpha=False,
            )

            image_path = os.path.join(
                output_dir,
                f"page_{page_index + 1:03d}.png"
            )

            pixmap.save(image_path)
            image_files.append(image_path)

    if not image_files:
        raise ValueError(
            f"PDF에서 변환된 페이지가 없습니다: {full_path}"
        )        

    print("==== PDF CONVERT SUCCESS ====")
    print(f"document_id: {document_id}")
    print(f"execution_id: {execution_id}")
    print(f"page_count: {len(image_files)}")
    print(f"output_dir: {output_dir}")

    return {
        "document_id": document_id,
        "execution_id": execution_id,
        "file_type": file_info["file_type"],
        "image_files": image_files
    }

def _prepare_single_image(file_info):
    image_path = file_info["file_path"]

    if not os.path.isfile(image_path):
        raise FileNotFoundError(
            f"이미지 파일을 찾을 수 없습니다: {image_path}"
        )

    print("==== IMAGE PREPARE SUCCESS ====")
    print(f"document_id: {file_info['document_id']}")
    print(f"execution_id: {file_info['execution_id']}")
    print(f"image_path: {image_path}")
    
    return {
        "document_id": file_info["document_id"],
        "execution_id": file_info["execution_id"],
        "file_type": file_info["file_type"],
        "image_files": [
            file_info["file_path"]
        ]
    }
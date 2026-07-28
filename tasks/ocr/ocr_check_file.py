import os
from tasks.common.constants import OCR_MEDIA_ROOT

def check_file(conf):

    document_id = conf["document_id"]
    execution_id = conf["execution_id"]
    file_path = conf["file_path"]
    saved_name = conf["saved_name"]
    file_type = conf["file_type"]

    print("file_type")

    full_path = os.path.join(
        OCR_MEDIA_ROOT,
        file_path,
        saved_name
    )

    if not os.path.exists(full_path):
        raise FileNotFoundError(full_path)

    print("FILE EXISTS")
    print(f"full_path: {full_path}")

    print("==== FILE CHECK SUCCESS ====")
    print(f"document_id: {document_id}")
    print(f"execution_id: {execution_id}")
    print(f"file_type: {file_type}")
    
    return {
        "document_id": document_id,
        "execution_id": execution_id,
        "file_path": full_path,
        "file_type": file_type
    }
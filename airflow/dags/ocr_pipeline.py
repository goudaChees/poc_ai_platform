import requests
from airflow.sdk import dag, task
from datetime import datetime
from tasks.common.pipeline_failure_callback import notify_pipeline_failed
from tasks.ocr.ocr_check_file import check_file as check_file_service
from tasks.ocr.ocr_prepare_image import prepare_image as prepare_image_service
from tasks.ocr.ocr_run import run_ocr as run_ocr_service
from tasks.ocr.ocr_save_result import save_result as save_result_service
from tasks.chunking.chunk_document import chunk_document as chunk_document_service
from tasks.embedding.embed_chunks import embed_chunks as embed_chunks_service

@dag(
    dag_id="ocr_pipeline",
    schedule=None,
    start_date=datetime(2026, 7, 21),
    catchup=False
)
def ocr_pipeline():

    @task(on_failure_callback=notify_pipeline_failed,)
    def check_file(**context):

        conf = context["dag_run"].conf

        print("==== DAG CONF ====")
        print(conf)

        return check_file_service(conf)

    @task(on_failure_callback=notify_pipeline_failed,)
    def prepare_image(file_info):

        print("==== DAG FILE INFO ====")
        print(f"prepare image : {file_info}")

        return prepare_image_service(file_info)

    @task(on_failure_callback=notify_pipeline_failed,)
    def run_ocr(image_info):

        print("==== OCR START ====")
        print(f"image info : {image_info}")

        return run_ocr_service(image_info)
    
    @task(on_failure_callback=notify_pipeline_failed,)
    def save_result(ocr_info):

        print("==== SAVE RESULT START ====")
        print(ocr_info)

        return save_result_service(ocr_info)

    @task(on_failure_callback=notify_pipeline_failed,)
    def chunking(saved_ocr_info):
        print("==== CHUNKING START ====")
        print(f"save info : {saved_ocr_info}")

        return chunk_document_service(saved_ocr_info)

    @task(on_failure_callback=notify_pipeline_failed)
    def embedding(chunk_info):
        print("==== EMBEDDING START ====")
        print(f"chunk_info : {chunk_info}")

        return embed_chunks_service(chunk_info)


    file_info  = check_file()

    image_info = prepare_image(file_info)
    
    ocr_info = run_ocr(image_info)

    saved_ocr_info = save_result(ocr_info)

    chunk_info = chunking(saved_ocr_info)

    embedding_info = embedding(chunk_info)

    # index_info = qdrant_index(embedding_info)

    # validation_info = rag_validation(index_info)

    # complete_pipeline(validation_info)


ocr_pipeline()
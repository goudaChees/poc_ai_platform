import requests
from airflow.sdk import dag, task
from datetime import datetime
from tasks.common.pipeline_failure_callback import notify_pipeline_failed
from tasks.common.stage_gate import is_stage_enabled, pass_through_pipeline_info
from tasks.ocr.ocr_check_file import check_file as check_file_service
from tasks.ocr.ocr_prepare_image import prepare_image as prepare_image_service
from tasks.ocr.ocr_run import run_ocr as run_ocr_service
from tasks.ocr.ocr_save_result import save_result as save_result_service
from tasks.chunking.chunk_document import chunk_document as chunk_document_service
from tasks.embedding.embed_chunks import embed_chunks as embed_chunks_service
from tasks.qdrant.index_embeddings import index_embeddings as index_embeddings_service
from tasks.rag.validate_index import validate_rag_index as validate_rag_index_service
from tasks.pipeline.complete_pipeline import complete_pipeline as complete_pipeline_service
from tasks.pipeline.update_pipeline_stage import update_pipeline_stage as update_pipeline_stage_service

@dag(
    dag_id="ocr_pipeline",
    schedule=None,
    start_date=datetime(2026, 7, 21),
    catchup=False
)
def ocr_pipeline():

    @task(on_failure_callback=notify_pipeline_failed,)
    def check_file(**context):

        dag_run = context["dag_run"]
        conf = dag_run.conf or {}

        print("==== DAG CONF ====")
        print(conf)

        if not is_stage_enabled(
            conf,
            "FILE_PREPARATION",
        ):
            raise ValueError(
                "필수 Stage가 Execution Plan에 "
                "없습니다: FILE_PREPARATION"
            )

        print("== PIPELINE STAGE 1 (FILE_PREPARATION) == ")
        update_pipeline_stage_service(
            pipeline_info=conf,
            stage="FILE_PREPARATION",
            airflow_run_id=dag_run.run_id,
        )

        return check_file_service(conf)

    @task(on_failure_callback=notify_pipeline_failed,)
    def prepare_image(file_info, **context):

        dag_run = context["dag_run"]
        conf = dag_run.conf or {}

        if not is_stage_enabled(
            conf,
            "DOCUMENT_CONVERSION",
        ):
            return pass_through_pipeline_info(
                file_info,
                task_name="prepare_image",
                stage_code=(
                    "DOCUMENT_CONVERSION"
                ),
            )


        print("==== DAG FILE INFO ====")
        print(f"prepare image : {file_info}")

        print("== PIPELINE STAGE 2 (PREPARE IMAGE) == ")
        update_pipeline_stage_service(
            pipeline_info=file_info,
            stage="DOCUMENT_CONVERSION",
            airflow_run_id=dag_run.run_id,
        )

        return prepare_image_service(file_info)

    @task(on_failure_callback=notify_pipeline_failed,)
    def run_ocr(image_info, **context):

        dag_run = context["dag_run"]
        conf = dag_run.conf or {}

        if not is_stage_enabled(
            conf,
            "OCR",
        ):
            return pass_through_pipeline_info(
                image_info,
                task_name="run_ocr",
                stage_code="OCR",
            )

        print("==== OCR START ====")
        print(f"image info : {image_info}")

        print("== PIPELINE STAGE 3 (OCR) == ")
        update_pipeline_stage_service(
            pipeline_info=image_info,
            stage="OCR",
            airflow_run_id=dag_run.run_id,
        )

        execution_plan = (conf.get("execution_plan") or {})
        stage_options = (execution_plan.get("stage_options") or {})
        ocr_options = (stage_options.get("OCR") or {})

        raw_provider_code = (
            ocr_options.get(
                "provider"
            )
        )

        if not isinstance(
            raw_provider_code,
            str,
        ):
            raise ValueError(
                "OCR provider 설정이 없습니다."
            )

        provider_code = (
            raw_provider_code
            .strip()
            .upper()
        )

        if not provider_code:
            raise ValueError(
                "OCR provider 설정이 "
                "비어 있습니다."
            )

        provider_options = (
            ocr_options.get("config")
            or {}
        )

        print(
            "OCR provider_code: "
            f"{provider_code}",
            flush=True,
        )

        print(
            "OCR provider_option_keys: "
            f"{sorted(provider_options.keys())}",
            flush=True,
        )

        return run_ocr_service(
            image_info,
            provider_code=provider_code,
            provider_options=provider_options,
        )
    
    @task(on_failure_callback=notify_pipeline_failed,)
    def save_result(ocr_info, **context):

        conf = context["dag_run"].conf or {}

        if not is_stage_enabled(
            conf,
            "OCR",
        ):
            return pass_through_pipeline_info(
                ocr_info,
                task_name="save_result",
                stage_code="OCR",
            )

        print("==== SAVE RESULT START ====")
        print(ocr_info)

        return save_result_service(ocr_info)

    @task(on_failure_callback=notify_pipeline_failed,)
    def chunking(saved_ocr_info, **context):

        dag_run = context["dag_run"]
        conf = dag_run.conf or {}

        if not is_stage_enabled(
            conf,
            "CHUNKING",
        ):
            return pass_through_pipeline_info(
                saved_ocr_info,
                task_name="chunking",
                stage_code="CHUNKING",
            )

        print("==== CHUNKING START ====")
        print(f"save info : {saved_ocr_info}")

        print("== PIPELINE STAGE 4 (CHUNKING) == ")
        update_pipeline_stage_service(
            pipeline_info=saved_ocr_info,
            stage="CHUNKING",
            airflow_run_id=dag_run.run_id,
        )

        return chunk_document_service(saved_ocr_info)

    @task(on_failure_callback=notify_pipeline_failed)
    def embedding(chunk_info, **context):

        dag_run = context["dag_run"]
        conf = dag_run.conf or {}

        if not is_stage_enabled(
            conf,
            "EMBEDDING",
        ):
            return pass_through_pipeline_info(
                chunk_info,
                task_name="embedding",
                stage_code="EMBEDDING",
            )

        print("==== EMBEDDING START ====")
        print(f"chunk_info : {chunk_info}")

        print("== PIPELINE STAGE 5 (EMBEDDING) == ")
        update_pipeline_stage_service(
            pipeline_info=chunk_info,
            stage="EMBEDDING",
            airflow_run_id=dag_run.run_id,
        )

        return embed_chunks_service(chunk_info)

    @task(on_failure_callback=notify_pipeline_failed)
    def qdrant_index(embedding_info, **context):

        dag_run = context["dag_run"]
        conf = dag_run.conf or {}

        if not is_stage_enabled(
            conf,
            "QDRANT_INDEX",
        ):
            return pass_through_pipeline_info(
                embedding_info,
                task_name="qdrant_index",
                stage_code="QDRANT_INDEX",
            )

        print("==== QDRANT INDEX START ====")
        print(f"embedding_info : {embedding_info}")

        print("== PIPELINE STAGE 6 (QDRANT_INDEX) == ")
        update_pipeline_stage_service(
            pipeline_info=embedding_info,
            stage="QDRANT_INDEX",
            airflow_run_id=dag_run.run_id,
        )

        return index_embeddings_service(embedding_info)

    @task(on_failure_callback=notify_pipeline_failed)
    def rag_validation(index_info, **context):

        dag_run = context["dag_run"]
        conf = dag_run.conf or {}

        if not is_stage_enabled(
            conf,
            "RAG_VALIDATION",
        ):
            return pass_through_pipeline_info(
                index_info,
                task_name="rag_validation",
                stage_code="RAG_VALIDATION",
            )

        print("==== RAG VALIDATION START ====")
        print(f"index_info: {index_info}")

        print("== PIPELINE STAGE 7 (RAG_VALIDATION) == ")
        update_pipeline_stage_service(
            pipeline_info=index_info,
            stage="RAG_VALIDATION",
            airflow_run_id=dag_run.run_id,
        )

        return validate_rag_index_service(index_info)

    @task(on_failure_callback=notify_pipeline_failed)
    def complete_pipeline(validation_info, **context,):

        dag_run = context["dag_run"]
        conf = dag_run.conf or {}

        if not is_stage_enabled(
            conf,
            "COMPLETE",
        ):
            raise ValueError(
                "필수 Stage가 Execution Plan에 "
                "없습니다: COMPLETE"
            )

        execution_plan = conf.get(
            "execution_plan"
        )

        if execution_plan is None:
            # 과거 수동 실행 등 Plan이 없는 경우에는
            # 기존 전체 Pipeline으로 취급한다.
            rag_validation_required = True
        else:
            resolved_stages = (
                execution_plan.get(
                    "resolved_stages"
                )
                or []
            )

            rag_validation_required = (
                "RAG_VALIDATION"
                in resolved_stages
            )

        print("==== COMPLETE PIPELINE START ====")
        print(f"validation_info: {validation_info}")
        print(f"airflow_run_id: {dag_run.run_id}")

        print("rag_validation_required: "
            f"{rag_validation_required}",
            flush=True,
        )

        return complete_pipeline_service(
            validation_info=validation_info,
            airflow_run_id=dag_run.run_id,
            rag_validation_required=(
                rag_validation_required
            ),
        )

    file_info  = check_file()

    image_info = prepare_image(file_info)
    
    ocr_info = run_ocr(image_info)

    saved_ocr_info = save_result(ocr_info)

    chunk_info = chunking(saved_ocr_info)

    embedding_info = embedding(chunk_info)

    index_info = qdrant_index(embedding_info)

    validation_info = rag_validation(index_info)

    complete_pipeline(validation_info)


ocr_pipeline()
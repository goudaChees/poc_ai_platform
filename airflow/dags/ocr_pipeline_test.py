from airflow.sdk import dag, task
from datetime import datetime


@dag(
    dag_id="ocr_pipeline_test",
    schedule=None,
    start_date=datetime(2026, 7, 20),
    catchup=False
)
def ocr_pipeline_test():

    @task
    def upload_check():
        print("파일 확인")

    @task
    def ai_analysis():
        print("AI 모델 분석")

    @task
    def save_result():
        print("결과 저장")

    upload_check() >> ai_analysis() >> save_result()


ocr_pipeline_test()
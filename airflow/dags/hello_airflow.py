from airflow.sdk import dag, task
from datetime import datetime


@dag(
    dag_id="hello_airflow",
    schedule=None,
    start_date=datetime(2026, 7, 16),
    catchup=False,
)
def hello_airflow():

    @task
    def hello():
        print("Hello Airflow")

    hello()


dag = hello_airflow()
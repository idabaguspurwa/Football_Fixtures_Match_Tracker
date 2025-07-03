# football_spark_dag.py
from __future__ import annotations

import datetime

from airflow.models.dag import DAG
from airflow.providers.google.cloud.operators.dataproc import (
    DataprocSubmitJobOperator,
)

# Define project and environment variables
PROJECT_ID = "footballfixtures"
REGION = "asia-southeast1"
CLUSTER_NAME = "spark-football-cluster"
BUCKET_NAME = "footballfixtures-data-pipeline-assets"
KAFKA_IP = "35.247.177.245" # Your Kafka VM IP

# Define the PySpark job details
PYSPARK_JOB = {
    "reference": {"job_id": "football_streaming_job_{{ ds_nodash }}_{{ task_instance.try_number }}"},
    "placement": {"cluster_name": CLUSTER_NAME},
    "pyspark_job": {
        "main_python_file_uri": f"gs://{BUCKET_NAME}/match_processor.py",
        "file_uris": [f"gs://{BUCKET_NAME}/schemas/event_schema.avsc"],
        "properties": {
            "spark.jars.packages": "org.apache.spark:spark-sql-kafka-0-10_2.12:3.3.2,org.apache.spark:spark-avro_2.12:3.3.2,com.google.cloud.spark:spark-bigquery-with-dependencies_2.12:0.34.0"
        },
        "args": [
            f"{KAFKA_IP}:9092",
            f"gs://{BUCKET_NAME}/checkpoints",
            f"{PROJECT_ID}.football_dataset.live_match_events",
        ],
    },
}

with DAG(
    dag_id="football_data_processing_dag",
    start_date=datetime.datetime(2025, 1, 1),
    schedule="@daily",  # This will run the job once a day
    catchup=False,
    tags=["dataproc", "football"],
) as dag:
    submit_spark_job = DataprocSubmitJobOperator(
        task_id="submit_spark_job",
        project_id=PROJECT_ID,
        region=REGION,
        job=PYSPARK_JOB,
    )
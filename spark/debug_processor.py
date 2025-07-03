# spark/debug_processor.py - A simple script to test the pipeline
import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import col

def main(kafka_bootstrap_servers, gcs_checkpoint_location, bq_table):
    spark = SparkSession.builder \
        .appName("FootballDebugProcessor") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")

    # Read from Kafka, but do NOT try to decode the value
    kafka_df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", kafka_bootstrap_servers) \
        .option("subscribe", "match_events") \
        .load()

    # Select the raw binary key and value to write to BigQuery
    output_df = kafka_df.select(
        col("key"),
        col("value")
    )

    # Write to the new debug table
    output_df.writeStream \
        .format("bigquery") \
        .option("table", bq_table) \
        .option("checkpointLocation", gcs_checkpoint_location) \
        .option("temporaryGcsBucket", "footballfixtures-data-pipeline-assets") \
        .outputMode("append") \
        .start() \
        .awaitTermination()

if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(-1)
    
    kafka_servers, gcs_checkpoint, bq_table_name = sys.argv[1], sys.argv[2], sys.argv[3]
    main(kafka_servers, gcs_checkpoint, bq_table_name)
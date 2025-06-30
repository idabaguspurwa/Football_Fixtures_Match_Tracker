# spark/match_processor.py
import sys
import json
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, udf
from pyspark.sql.types import StructType, StructField, StringType, IntegerType
from fastavro import schemaless_reader
from io import BytesIO

def deserialize_avro(message):
    try:
        # Open the schema file made available by Spark's --files option.
        with open('event_schema.avsc', 'r') as f:
            schema = json.load(f)
        
        bytes_io = BytesIO(message)
        decoded_data = schemaless_reader(bytes_io, schema)
        return json.dumps(decoded_data)
    except Exception:
        return None

def main(kafka_bootstrap_servers, gcs_checkpoint_location, bq_table):
    spark = SparkSession.builder \
        .appName("FootballMatchProcessor") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")

    deserialize_udf = udf(deserialize_avro, StringType())

    kafka_df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", kafka_bootstrap_servers) \
        .option("subscribe", "match_events") \
        .option("startingOffsets", "latest") \
        .load()

    decoded_df = kafka_df.withColumn("decoded_value", deserialize_udf(col("value")))

    json_schema = StructType([
        StructField("fixture_id", IntegerType()),
        StructField("event_time", IntegerType()),
        StructField("team_name", StringType()),
        StructField("player_name", StringType()),
        StructField("event_type", StringType()),
        StructField("detail", StringType())
    ])

    output_df = decoded_df \
        .withColumn("data", from_json(col("decoded_value"), json_schema)) \
        .select("data.*") \
        .filter(col("fixture_id").isNotNull())

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
        print("Usage: spark-submit match_processor.py <kafka_bootstrap_servers> <gcs_checkpoint_location> <bq_table>", file=sys.stderr)
        sys.exit(-1)
    
    kafka_servers = sys.argv[1]
    gcs_checkpoint = sys.argv[2]
    bq_table_name = sys.argv[3]
    main(kafka_servers, gcs_checkpoint, bq_table_name)
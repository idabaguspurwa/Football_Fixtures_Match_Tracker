import sys
import json
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, udf
from pyspark.sql.types import StructType, StructField, StringType, IntegerType
from fastavro import schemaless_reader
from io import BytesIO
from pyspark import SparkFiles

def deserialize_avro(message, schema):
    try:
        # Skips the 5-byte Confluent header
        bytes_io = BytesIO(message[5:])
        decoded_data = schemaless_reader(bytes_io, schema)
        
        if 'player_name' not in decoded_data:
            decoded_data['player_name'] = None
            
        return json.dumps(decoded_data)
    except Exception as e:
        print(f"ERROR: Could not decode Avro message. Error: {e}")
        return None

def main(kafka_bootstrap_servers, gcs_checkpoint_location, bq_table, schema_gcs_path):
    spark = SparkSession.builder \
        .appName("FootballMatchProcessor-Final-Robust") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")

    spark.sparkContext.addFile(schema_gcs_path)
    
    # Read and parse the schema ONCE on the driver.
    with open(SparkFiles.get("event_schema.avsc"), "r") as f:
        parsed_schema = json.load(f)

    deserialize_udf = udf(lambda msg: deserialize_avro(msg, parsed_schema), StringType())

    kafka_df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", kafka_bootstrap_servers) \
        .option("subscribe", "match_events") \
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
    if len(sys.argv) != 5:
        print("Usage: spark-submit ... <kafka_servers> <gcs_checkpoint> <bq_table> <schema_gcs_path>", file=sys.stderr)
        sys.exit(-1)
    
    kafka_servers, gcs_checkpoint, bq_table_name, schema_path = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    main(kafka_servers, gcs_checkpoint, bq_table_name, schema_path)

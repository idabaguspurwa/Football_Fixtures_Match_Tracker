# producer/producer.py - The full script with diagnostics
import os
import requests
import json
import time
from confluent_kafka import avro
from confluent_kafka.avro import AvroProducer

print("--- Script starting ---")

# --- Kafka & Schema Registry Configuration ---
KAFKA_BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS")
SCHEMA_REGISTRY_URL = os.environ.get("SCHEMA_REGISTRY_URL")
KAFKA_TOPIC = "match_events"

# --- API-Football Configuration ---
API_KEY = os.environ.get("API_FOOTBALL_KEY")
API_HOST = "api-football-v1.p.rapidapi.com"
HEADERS = {'x-rapidapi-host': API_HOST, 'x-rapidapi-key': API_KEY}
URL = f"https://{API_HOST}/v3/fixtures"
PARAMS = {"live": "all"}

# Load Avro schema
value_schema = avro.load('schemas/event_schema.avsc')

print("--- Initializing AvroProducer ---")
# Create AvroProducer
producer = AvroProducer({
    'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
    'schema.registry.url': SCHEMA_REGISTRY_URL
}, default_value_schema=value_schema)
print("--- AvroProducer initialized ---")

sent_events = set()
print("--- Starting to fetch live match data... ---")

while True:
    try:
        print("--- Making API call ---")
        response = requests.get(URL, headers=HEADERS, params=PARAMS)
        response.raise_for_status()
        live_fixtures = response.json().get("response", [])
        
        print(f"--- Found {len(live_fixtures)} live fixtures ---")
        
        if not live_fixtures:
            print("--- No live matches currently. ---")
        
        for fixture in live_fixtures:
            fixture_id = fixture['fixture']['id']
            for event in fixture.get('events', []):
                event_id = f"{fixture_id}-{event['time']['elapsed']}-{event.get('player', {}).get('id', 'N/A')}-{event['type']}"
                
                if event_id not in sent_events:
                    event_data = {
                        "fixture_id": fixture_id,
                        "event_time": event['time']['elapsed'],
                        "team_name": event['team']['name'],
                        "player_name": event.get('player', {}).get('name'),
                        "event_type": event['type'],
                        "detail": event['detail']
                    }
                    
                    producer.produce(topic=KAFKA_TOPIC, value=event_data)
                    print(f"--- Sent Event: {event_data['detail']} for fixture {fixture_id} ---")
                    sent_events.add(event_id)

        producer.flush(10)

    except requests.exceptions.RequestException as e:
        print(f"--- ERROR fetching data: {e} ---")
    except Exception as e:
        print(f"--- An unexpected ERROR occurred: {e} ---")

    time.sleep(65)
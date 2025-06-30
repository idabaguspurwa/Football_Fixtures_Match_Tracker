terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 4.50.0"
    }
  }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

// --- 1. Networking & Firewall ---
resource "google_compute_firewall" "allow_kafka" {
  name    = "allow-kafka-ports"
  network = "default"
  allow {
    protocol = "tcp"
    ports    = ["22", "9092", "2181", "8081"] // Kafka, Zookeeper, Schema Registry
  }
  source_ranges = ["0.0.0.0/0"] // For simplicity; in production, restrict this
}


// --- 2. GCS, BigQuery, Artifact Registry ---
resource "google_storage_bucket" "pipeline_bucket" {
  name          = "${var.gcp_project_id}-football-pipeline-bucket"
  location      = "ASIA-SOUTHEAST1"
  force_destroy = true
}

resource "google_bigquery_dataset" "football_dataset" {
  dataset_id = "football_dataset"
  location   = "asia-southeast1"
}

resource "google_bigquery_table" "live_match_events" {
  dataset_id = google_bigquery_dataset.football_dataset.dataset_id
  table_id   = "live_match_events"
  schema = file("${path.module}/schemas/bigquery_schema.json")
}

resource "google_storage_bucket" "pipeline_assets" {
  # Use the recommended name or your own unique name
  name          = "footballfixtures-data-pipeline-assets"
  location      = "ASIA-SOUTHEAST1"
  force_destroy = true
}

resource "google_artifact_registry_repository" "producer_repo" {
  location      = var.gcp_region
  repository_id = "football-producer-repo"
  format        = "DOCKER"
}


// --- 3. Kafka & Schema Registry VM ---
resource "google_compute_instance" "kafka_vm" {
  name         = "kafka-schema-registry-server"
  machine_type = "e2-standard-2" // Needs more RAM for Kafka + SR
  zone         = "${var.gcp_region}-a"
  tags         = ["kafka"]

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-11"
      size  = 20 // Increase disk size
    }
  }

  network_interface {
    network = "default"
    access_config {}
  }
  
  // This startup script installs everything needed on the VM
  metadata_startup_script = file("${path.module}/scripts/install_kafka_confluent.sh")
}


// --- 4. Dataproc & Composer (Optional but good for full setup) ---
resource "google_dataproc_cluster" "spark_cluster" {
  name   = "spark-football-cluster"
  region = var.gcp_region

  cluster_config {
    gce_cluster_config {
      zone = "${var.gcp_region}-a"
    }

    master_config {
      num_instances = 1
      machine_type  = "e2-standard-4"
    }
    worker_config {
      num_instances = 2
      machine_type  = "e2-standard-4"
    }
    software_config {
        image_version = "2.1-debian11"
    }
  }
}
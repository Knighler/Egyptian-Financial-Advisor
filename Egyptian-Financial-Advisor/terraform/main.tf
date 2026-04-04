terraform {

    backend "gcs" {
    bucket  = "	de-practice-490214-terraform-state"
    prefix  = "terraform/state"
  }
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "5.6.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = "US-central1"
}

resource "google_storage_bucket" "efa-bucket" {
  name          = "${var.project_id}-efa-bucket"
  location      = "US"
  force_destroy = true 

  lifecycle_rule {

    action {
      type = "AbortIncompleteMultipartUpload"
    }
  }
}

resource "google_bigquery_dataset" "efa_raw_dataset" {
  dataset_id = "efa_raw_dataset"
  location   = "US"
}

resource "google_bigquery_dataset" "efa_dataset" {
  dataset_id = "efa_dataset"
  location   = "US"
}

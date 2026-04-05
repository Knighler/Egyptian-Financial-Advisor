terraform {
    backend "gcs" {
    
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

    condition {
      age = 1 
    }
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


# KESTRA  VM 
resource "google_compute_instance" "kestra_vm" {
  name         = "kestra-orchestrator"
  machine_type = "e2-medium"
  zone         = "US" 

  boot_disk {
    initialize_params {
      # Use a stable Ubuntu image
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
      size  = 30 
    }
  }

  network_interface {
    network = "default"
    access_config {
      # Auto public IP
    }
  }

  # Allow GitHub Actions to connect securely
  tags = ["kestra-server"]

  # The "Magic" Startup Script: Installs Docker automatically when the VM turns on
  metadata_startup_script = <<-EOT
    #!/bin/bash
    apt-get update
    apt-get install -y docker.io docker-compose-v2 git
    systemctl start docker
    systemctl enable docker
  EOT
}

# Firewall
resource "google_compute_firewall" "kestra_ui" {
  name    = "allow-kestra-8080"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["8080", "22"] # 8080 for UI, 22 for GitHub Actions SSH
  }

  # Apply this firewall rule to our new VM
  target_tags   = ["kestra-server"]
  source_ranges = ["0.0.0.0/0"] 
}
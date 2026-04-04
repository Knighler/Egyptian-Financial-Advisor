variable "project_id" {
  type        = string
  description = "The GCP Project ID"
}

variable "gcp_key_json" {
  type        = string
  description = "The Service Account JSON key content"
  sensitive   = true # This hides the value from Terraform logs
}
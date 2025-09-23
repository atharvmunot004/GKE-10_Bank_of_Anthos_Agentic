# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# GCS bucket used as skaffold build cache for main branch
resource "google_storage_bucket" "build_cache_main" {
  name                        = "build-cache-main-${var.project_id}"
  uniform_bucket_level_access = true
  location                    = var.region
  force_destroy              = true
}

# Initialize cache with empty file
resource "google_storage_bucket_object" "cache_main" {
  bucket = google_storage_bucket.build_cache_main.name

  name    = local.cache_filename
  content = " "

  lifecycle {
    # do not reset cache when running terraform
    ignore_changes = [
      content,
      detect_md5hash
    ]
  }
}

# service_account for main branch deployments
resource "google_service_account" "cloud_build_main" {
  account_id = "cloud-build-main"
}

# IAM roles for main branch service account
resource "google_project_iam_member" "cloud_build_main_roles" {
  for_each = toset([
    "roles/container.developer",
    "roles/storage.admin",
    "roles/artifactregistry.admin",
    "roles/clouddeploy.developer",
    "roles/clouddeploy.approver",
    "roles/clouddeploy.releaser"
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.cloud_build_main.email}"
}

# give CloudBuild SA access to skaffold cache
resource "google_storage_bucket_iam_member" "build_cache_main" {
  bucket = google_storage_bucket.build_cache_main.name

  member = "serviceAccount:${google_service_account.cloud_build_main.email}"
  role   = "roles/storage.admin"
}

# Main branch CI/CD trigger configuration
resource "google_cloudbuild_trigger" "ci-main" {
  name     = "main-branch-cicd"
  location = var.region

  github {
    owner = var.repo_owner
    name  = var.sync_repo

    push {
      branch = "^${var.sync_branch}$"
    }
  }
  
  filename = ".github/cloudbuild/ci-main.yaml"
  
  substitutions = {
    _CACHE_URI            = "gs://${google_storage_bucket.build_cache_main.name}/${google_storage_bucket_object.cache_main.name}"
    _CONTAINER_REGISTRY   = "${google_artifact_registry_repository.container_registry.location}-docker.pkg.dev/${google_artifact_registry_repository.container_registry.project}/${google_artifact_registry_repository.container_registry.repository_id}"
    _CACHE               = local.cache_filename
    _REGION              = var.region
  }
  
  service_account = google_service_account.cloud_build_main.id
}

# Cloud Deploy delivery pipeline for main branch
resource "google_clouddeploy_delivery_pipeline" "main_pipeline" {
  project  = var.project_id
  location = var.region
  name     = "main-branch-pipeline"
  
  serial_pipeline {
    stages {
      profiles  = ["staging"]
      target_id = "staging"
      strategy {
        standard {
          verify = true
        }
      }
    }
    stages {
      profiles  = ["production"]
      target_id = "production"
      strategy {
        standard {
          verify = false
        }
      }
    }
  }
  
  provider = google-beta
}

# Note: google_clouddeploy_release is not supported in current provider version
# Releases will be created manually via Cloud Deploy console or gcloud CLI

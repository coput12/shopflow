# Терраформ-стейт храним локально. Для продакшена — используй remote state (s3/yc bucket).
terraform {
  required_version = ">= 1.7"
  required_providers {
    yandex = {
      source  = "yandex-cloud/yandex"
      version = "~> 0.135"
    }
  }
}

provider "yandex" {
  token     = var.yc_token          # или export YC_TOKEN
  cloud_id  = var.yc_cloud_id
  folder_id = var.yc_folder_id
  zone      = var.yc_zone
}
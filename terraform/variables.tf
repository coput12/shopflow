variable "yc_token" {
  description = "OAuth или IAM-токен Yandex Cloud"
  sensitive   = true
}

variable "yc_cloud_id" {
  description = "ID облака Yandex Cloud"
}

variable "yc_folder_id" {
  description = "ID папки (folder) Yandex Cloud"
  default     = "default"
}

variable "yc_zone" {
  default = "ru-central1-a"
}

variable "vm_image_id" {
  description = "Ubuntu 22.04 LTS. Получить: yc compute image list --folder-id standard-images"
  default     = "fd8v7m1h1t8q4r09t5q3"
}

variable "vm_user" {
  default = "ubuntu"
}

variable "vm_public_key" {
  description = "Публичный SSH-ключ для доступа к VM"
}

variable "vm_cores"   { default = 2 }
variable "vm_memory"  { default = 4 }
variable "vm_name"    { default = "shopflow-vm" }
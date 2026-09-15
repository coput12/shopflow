resource "yandex_compute_instance" "shopflow" {
  name        = var.vm_name
  platform_id = "standard-v3"
  zone        = var.yc_zone

  resources {
    cores  = var.vm_cores
    memory = var.vm_memory
  }

  boot_disk {
    initialize_params {
      image_id = var.vm_image_id
      size     = 20
      type     = "network-ssd"
    }
  }

  network_interface {
    subnet_id          = yandex_vpc_subnet.shopflow.id
    nat                = true
    security_group_ids = [yandex_vpc_security_group.shopflow.id]
  }

  metadata = {
    ssh-keys = "${var.vm_user}:${var.vm_public_key}"
    serial-port-enable = "1"
  }
}

resource "yandex_vpc_security_group" "shopflow" {
  name       = "shopflow-sg"
  network_id = yandex_vpc_network.shopflow.id

  ingress {
    protocol       = "TCP"
    port           = 22
    v4_cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    protocol       = "TCP"
    port           = 8080
    v4_cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    protocol       = "TCP"
    port           = 3000
    v4_cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    protocol       = "ANY"
    v4_cidr_blocks = ["0.0.0.0/0"]
  }
}
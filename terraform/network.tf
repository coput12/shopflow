resource "yandex_vpc_network" "shopflow" {
  name = "shopflow-net"
}

resource "yandex_vpc_subnet" "shopflow" {
  name           = "shopflow-subnet"
  zone           = var.yc_zone
  network_id     = yandex_vpc_network.shopflow.id
  v4_cidr_blocks = ["10.130.0.0/24"]
}
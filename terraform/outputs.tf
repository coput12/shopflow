output "vm_public_ip" {
  description = "Публичный IP созданной VM"
  value       = yandex_compute_instance.shopflow.network_interface[0].nat_ip_address
}

output "vm_ssh" {
  description = "Команда SSH для входа"
  value       = "ssh ${var.vm_user}@${yandex_compute_instance.shopflow.network_interface[0].nat_ip_address}"
}
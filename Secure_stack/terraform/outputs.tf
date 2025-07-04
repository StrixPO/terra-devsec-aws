output "nat_instance_id" {
  value = module.vpc.nat_instance_id
}

output "securepaste_api_url" {
  value = module.app-lambda_create.api_url
}

variable "cloudflare_api_token" {
  sensitive = true
}

variable "cloudflare_zone_id" {}

variable "frontend_domain_name" {
  description = "CloudFront distribution domain name"
}
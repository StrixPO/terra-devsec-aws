variable "project" {
  
}

variable "custom_domain" {
  type        = string
  description = "Custom domain to be added to CloudFront alias"
  default     = null
}

# variable "acm_certificate_arn" {
#   type        = string
#   description = "ACM certificate ARN for the custom domain"
#   default     = null
# }



variable "cloudflare_zone_id" {}
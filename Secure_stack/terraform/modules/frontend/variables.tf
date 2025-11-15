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

variable "certificate_arn" {
  type        = string
  description = "The ARN of the validated ACM certificate in us-east-1 for CloudFront"
}
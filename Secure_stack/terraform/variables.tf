
variable "project" {
}

variable "vpc_cidr" {
}

variable "aws_region" {
  type    = string
}
variable "public_subnets" {
}

variable "private_subnets" {
}

variable "azs" {
}

variable "nat_ami_id" {
}

variable "key_name" {
}

variable "key_path" {
}

variable "ami_id" {
}

variable "create_zip_path" {
  description = "Path to Lambda zip file"
  type        = string
}

variable "get_zip_path" {
  description = "Path to Lambda zip file"
  type        = string
}

variable "domain_name" {
  type = string
}

variable "acm_certificate_arn" {
  type        = string
  description = "ACM certificate ARN for the frontend CloudFront"
}

variable "route53_zone_id" {
  type        = string
  description = "Route 53 hosted zone ID for the domain"
}

variable "custom_domain" {
  type        = string
  description = "The domain name used for the frontend site"
}
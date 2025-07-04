variable "project" {
  default = "securestack"
}

variable "vpc_cidr" {
  default = "10.0.0.0/16"
}

variable "public_subnets" {
  default = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnets" {
  default = ["10.0.101.0/24", "10.0.102.0/24"]
}

variable "azs" {
  default = ["us-east-1a", "us-east-1b"]
}

variable "nat_ami_id" {
  default = "ami-0b0dcb5067f052a63" # NAT AMI (for us-east-1)
}

variable "key_name" {
  default = "secure-stack" 
}

variable "key_path" {
    default = "~/.ssh/secure-stack.pem"
}

variable "ami_id" {
  default = "ami-0b0dcb5067f052a63" # Amazon Linux 2 in us-east-1
}

variable "create_zip_path" {
  description = "Path to Lambda zip file"
  type        = string
  default     = "../app/lambda/create/function.zip"
}

variable "get_zip_path" {
  description = "Path to Lambda zip file"
  type        = string
  default     = "../app/lambda/get/function.zip"
}


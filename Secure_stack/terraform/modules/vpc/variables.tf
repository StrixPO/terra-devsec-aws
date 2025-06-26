variable "project" {}
variable "vpc_cidr" {}
variable "public_subnets" {}
variable "private_subnets" {}
variable "azs" {}

variable "nat_instance_id" {
  description = "ID of the NAT instance"
  type        = string
}

variable "nat_ami_id" {}
variable "public_subnet_id" {}
variable "key_name" {}
variable "project" {}
variable "vpc_id" {}
variable "private_subnets" {
  type = list(string)
}
variable "app_ami_id" {
  description = "AMI ID for the EC2 instance (non-core / optional)"
  type        = string
}

variable "key_name" {
  description = "SSH key name (consider replacing with SSM)"
  type        = string
}

variable "project" {
  description = "Project name prefix for tagging/naming"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID for the security group"
  type        = string
}

variable "bastion_sg_id" {
  description = "Security group ID allowed to SSH into this instance"
  type        = string
}

variable "subnet_id" {
  description = "Subnet ID where the instance will be launched"
  type        = string
}

# This looks unused in the snippet you showed.
# If it's not used, delete it—unused variables reduce repo trust.
variable "execution_arn" {
  description = "Unused? Remove if not referenced."
  type        = string
}

variable "project" {
  description = "Project name"
  type        = string
}

variable "create_zip_path" {
  description = "Path to the zipped Lambda binary"
  type        = string
}

variable "bucket_name" {
  description = "S3 bucket name for paste storage"
  type        = string
}

variable "table_name" {
  description = "DynamoDB table name for paste metadata"
  type        = string
}

variable "dynamodb_table_arn" {
  description = "Dynamodb arn number"
}

variable "bucket_arn" {
  
}
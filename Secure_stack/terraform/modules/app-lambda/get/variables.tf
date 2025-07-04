variable "project" {}
variable "table_name" {}
variable "api_id" {}
variable "api_execution_arn" {}
variable "lambda_role_arn" {}
variable "get_zip_path" {
  description = "Path to zipped Lambda function"
  type        = string
}
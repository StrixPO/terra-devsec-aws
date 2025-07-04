output "secure_paste_policy_arn" {
  value = aws_iam_policy.secure_paste_access.arn
}

output "bucket_name" {
  value = aws_s3_bucket.secure_paste.id
}

output "table_name" {
  value = aws_dynamodb_table.paste_metadata.name
}

output "bucket_arn" {
  value = aws_s3_bucket.secure_paste.arn
}

output "dynamodb_table_arn" {
  value = aws_dynamodb_table.paste_metadata.arn
}
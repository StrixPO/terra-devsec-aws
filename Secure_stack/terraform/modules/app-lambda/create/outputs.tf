output "api_url" {
  value = aws_apigatewayv2_api.http_api.api_endpoint
}

output "api_id" {
  value = aws_apigatewayv2_api.http_api.id
}

output "execution_arn" {
  value = aws_apigatewayv2_api.http_api.execution_arn
}

output "lambda_exec_arn" {
  value = aws_iam_role.lambda_exec.arn
}
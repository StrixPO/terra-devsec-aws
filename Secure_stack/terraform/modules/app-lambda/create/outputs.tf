output "api_url" {
  value = aws_apigatewayv2_api.http_api.api_endpoint
}

output "api_id" {
  value = aws_apigatewayv2_api.http_api.id
}

output "execution_arn" {
  value = "arn:aws:apigateway:${var.region}::/apis/${aws_apigatewayv2_api.http_api.id}/stages/${aws_apigatewayv2_stage.default.name}"
}

output "lambda_exec_arn" {
  value = aws_iam_role.lambda_exec.arn
}

output "lambda_name" {
  value = aws_lambda_function.paste_create.function_name
}

output "lambda_exec_name" {
  value = aws_iam_role.lambda_exec.name
}

output "lambda_access_policy_arn" {
  value = aws_iam_policy.lambda_access.arn
}

output "execute_arn" {
  value = "${aws_apigatewayv2_api.http_api.execution_arn}"
}
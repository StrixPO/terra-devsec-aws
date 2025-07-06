resource "aws_lambda_function" "get_paste" {
  function_name = "${var.project}-paste-get"
  filename      = var.get_zip_path
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.12"
  role          = var.lambda_role_arn

  environment {
    variables = {
      TABLE_NAME = var.table_name
    }
  }
}


##########API GATEWAY###########################

resource "aws_apigatewayv2_integration" "lambda_get_integration" {
  api_id                 = var.api_id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.get_paste.invoke_arn
  integration_method     = "POST" # 🔧 MUST match the route!
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "get_paste_route" {
  api_id    = var.api_id
  route_key = "GET /paste/{paste_id}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_get_integration.id}"

  depends_on = [aws_apigatewayv2_integration.lambda_get_integration]
}
resource "aws_lambda_permission" "allow_api_get" {
  statement_id  = "AllowAPIInvokePasteGet"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_paste.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${var.api_execution_arn}/*/*"
}

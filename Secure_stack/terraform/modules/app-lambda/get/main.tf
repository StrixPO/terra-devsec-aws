resource "aws_lambda_function" "get_paste" {
  function_name = "${var.project}-get-paste"
  filename      = var.get_zip_path
  handler = "lambda_function.lambda_handler"
  runtime = "python3.12"
  role          = var.lambda_exec_arn
  timeout       = 10

  source_code_hash = filebase64sha256(var.get_zip_path)

  environment {
    variables = {
      BUCKET_NAME = var.bucket_name
      TABLE_NAME  = var.table_name
    }
  }
depends_on = [aws_iam_role_policy_attachment.attach_lambda_access_get]
}

resource "aws_apigatewayv2_integration" "lambda_get_integration" {
  api_id                 = var.api_id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.get_paste.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
}

# Route
resource "aws_apigatewayv2_route" "get_paste_route" {
  api_id    = var.api_id
  route_key = "POST /paste"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_get_integration.id}"
}

# Lambda permission
resource "aws_lambda_permission" "allow_api_get" {
  statement_id  = "AllowAPIInvokePasteGet"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_paste.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${var.api_execution_arn}/*/*"
}

resource "aws_iam_role_policy_attachment" "attach_lambda_access_get" {
  role       = var.lambda_exec_name
  policy_arn = var.lambda_access_policy_arn
}



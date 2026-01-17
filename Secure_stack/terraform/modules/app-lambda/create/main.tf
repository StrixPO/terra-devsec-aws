# -----------------------------------------------------------------------------
# Lambda execution role (trust policy only)
# -----------------------------------------------------------------------------
# Note: permissions are attached via aws_iam_role_policy_attachment below.
resource "aws_iam_role" "lambda_exec" {
  name = "${var.project}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action = "sts:AssumeRole",
      Effect = "Allow",
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

# -----------------------------------------------------------------------------
# Paste Create Lambda
# -----------------------------------------------------------------------------
resource "aws_lambda_function" "paste_create" {
  function_name = "${var.project}-paste-create"
  filename      = var.create_zip_path
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.12"
  role          = aws_iam_role.lambda_exec.arn
  timeout       = 10

  # ENV vars are the interface between infra and code.
  # SECURITY NOTE: Do NOT put secrets here; use SSM/Secrets Manager if needed.
  environment {
    variables = {
      BUCKET_NAME = var.bucket_name
      TABLE_NAME  = var.table_name
    }
  }

  # Ensures Lambda redeploys when the zip changes
  source_code_hash = filebase64sha256(var.create_zip_path)

  depends_on = [aws_iam_role.lambda_exec]
}

# -----------------------------------------------------------------------------
# HTTP API Gateway (v2)
# -----------------------------------------------------------------------------
resource "aws_apigatewayv2_api" "http_api" {
  name          = "${var.project}-api"
  protocol_type = "HTTP"

  # CORS is wide open for dev simplicity.
  # SECURITY NOTE: For a real deployment, lock allow_origins to your frontend domain(s).
  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["GET", "POST", "OPTIONS"]
    allow_headers = ["*"]
    expose_headers = ["*"]
    max_age        = 3600
  }
}

# Lambda proxy integration (payload format v2.0 matches your event parsing)
resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id                 = aws_apigatewayv2_api.http_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.paste_create.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "create_paste_route" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "POST /create"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http_api.id
  name        = "$default"
  auto_deploy = true

  # Basic throttling protects Lambda and DynamoDB from abuse.
  default_route_settings {
    throttling_burst_limit = 50
    throttling_rate_limit  = 10
  }
}

# Allow API Gateway to invoke the Lambda.
# NOTE:
# If you add more routes, keep permissions consistent (either specific per-route or broad per-API).
resource "aws_lambda_permission" "allow_apigw_invoke" {
  statement_id  = "AllowAPIGatewayInvokeCreate"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.paste_create.function_name
  principal     = "apigateway.amazonaws.com"

  # This is route-specific. Works, but can be annoying when you add new routes.
  source_arn = "${aws_apigatewayv2_api.http_api.execution_arn}/*/*/create"
}

resource "aws_iam_role" "lambda_exec" {
    name = "${var.project}-lambda-role"
    assume_role_policy = jsonencode({
        Version = "2012-10-17",
        Statement = [{
            Action = "sts:AssumeRole",
            Effect = "Allow",
            Principal ={
                Service = "lambda.amazonaws.com"
            }
        }]
    })
}

resource "aws_lambda_function" "paste_create" {
  function_name = "${var.project}-paste-create"
  filename      = var.create_zip_path
  handler = "lambda_function.lambda_handler"
  runtime = "python3.12"
  role          = aws_iam_role.lambda_exec.arn
  timeout       = 10

  environment {
    variables = {
      BUCKET_NAME = var.bucket_name
      TABLE_NAME  = var.table_name
    }
  }
  source_code_hash = filebase64sha256(var.create_zip_path)

  depends_on = [aws_iam_role.lambda_exec]
}

####API GATEWAY########

resource "aws_apigatewayv2_api" "http_api" {
    name = "${var.project}-api"
    protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["GET", "POST", "OPTIONS"]
    allow_headers = ["*"]
    expose_headers = ["*"]
    max_age        = 3600
  }
}

resource "aws_apigatewayv2_integration" "lambda_integration" {
    api_id = aws_apigatewayv2_api.http_api.id 
    integration_type = "AWS_PROXY"
    integration_uri = aws_lambda_function.paste_create.invoke_arn 
    integration_method = "POST"
    payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "create_paste_route" {
    api_id = aws_apigatewayv2_api.http_api.id 
    route_key  = "POST /create"
    target = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource  "aws_apigatewayv2_stage" "default" {
    api_id = aws_apigatewayv2_api.http_api.id 
    name = "$default"
    auto_deploy = true 

    default_route_settings {
      throttling_burst_limit = 1 # req per burst
      throttling_rate_limit = 2  # req per sec
    }
}



resource "aws_lambda_permission" "allow_apigw_invoke" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.paste_create.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http_api.execution_arn}/*/*/create"
}

########IAM ROLES#############



data "aws_iam_policy_document" "lambda_s3_dynamo_policy" {
  statement {
    sid    = "AllowPutAndGetObject"
    actions = [
      "s3:PutObject",
      "s3:GetObject"
    ]
    resources = ["${var.bucket_arn}/*"]

    # Optional KMS enforcement
    condition {
      test     = "StringEquals"
      variable = "s3:x-amz-server-side-encryption"
      values   = ["aws:kms"]
    }
  }

  statement {
    sid     = "DynamoMinimal"
    actions = [
      "dynamodb:PutItem",
      "dynamodb:GetItem",
      "dynamodb:UpdateItem"
    ]
    resources = [var.dynamodb_table_arn]
  }

  statement {
    sid     = "LogsMinimal"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = [
      "arn:aws:logs:${var.region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/*"
    ]
  }
}


resource "aws_iam_policy" "lambda_access" {
    name = "${var.project}-lambda-access"
    policy = data.aws_iam_policy_document.lambda_s3_dynamo_policy.json
}

resource "aws_iam_role_policy_attachment" "attach_lambda_access" {
    role = aws_iam_role.lambda_exec.name
    policy_arn = aws_iam_policy.lambda_access.arn
}
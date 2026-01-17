# Alarm that triggers on Lambda errors
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "${var.project}-lambda-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 60
  statistic           = "Sum"
  threshold           = 1

  dimensions = {
    FunctionName = var.lambda_name
  }

  alarm_description   = "Lambda function has errors"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn] # 🔁 Combine with alarm setup
}

# SNS topic for alerts
resource "aws_sns_topic" "alerts" {
  name = "${var.project}-alerts"
}

# SNS email subscription (requires confirmation by email)
resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.sns_endpoint_email
}

resource "aws_wafv2_web_acl" "securepaste" {
  provider    = aws.global
  name        = "securepaste-waf"
  description = "WAF ACL for SecurePaste"
  scope       = "CLOUDFRONT"

  default_action {
    allow {}
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "SecurePasteACL"
    sampled_requests_enabled   = true
  }

  rule {
    name     = "RateLimit100"
    priority = 0

    action {
      block {}
    }

    statement {
      rate_based_statement {
        limit              = 100
        aggregate_key_type = "IP"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "RateLimit100"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "AWSManagedRulesCommon"
    priority = 1

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSManagedRulesCommon"
      sampled_requests_enabled   = true
    }
  }
}

resource "aws_wafv2_web_acl_association" "cf_assoc" {
  provider     = aws.global
  resource_arn = var.cloudfront_distribution_arn
  web_acl_arn  = aws_wafv2_web_acl.securepaste.arn
}

terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
    }
  }
}


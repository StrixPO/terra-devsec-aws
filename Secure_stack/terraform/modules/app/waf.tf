# InCase Rest api is used (future clause more expensive)


# resource "aws_wafv2_web_acl" "securepaste" {
#   name  = "securepaste-waf"
#   scope = "REGIONAL"
#   description = "WAF ACL for SecurePaste"

#   default_action {
#     allow {}
#   }

#   visibility_config {
#     cloudwatch_metrics_enabled = true
#     metric_name                = "SecurePasteACL"
#     sampled_requests_enabled   = true
#   }

#   rule {
#     name     = "RateLimit100"
#     priority = 0

#     action {
#       block {}
#     }

#     statement {
#       rate_based_statement {
#         limit              = 100
#         aggregate_key_type = "IP"
#       }
#     }

#     visibility_config {
#       cloudwatch_metrics_enabled = true
#       metric_name                = "RateLimit100"
#       sampled_requests_enabled   = true
#     }
#   }

#   rule {
#     name     = "OWASPCommonRules"
#     priority = 1

#     override_action {
#       none {}
#     }

#     statement {
#       managed_rule_group_statement {
#         name        = "AWSManagedRulesCommonRuleSet"
#         vendor_name = "AWS"
#       }
#     }

#     visibility_config {
#       cloudwatch_metrics_enabled = true
#       metric_name                = "OWASPCommonRules"
#       sampled_requests_enabled   = true
#     }
#   }
# }

# resource "aws_wafv2_web_acl_association" "api_assoc" {
#   resource_arn = var.execution_arn
#   web_acl_arn  = aws_wafv2_web_acl.securepaste.arn
# }
# ACM Certificate in us-east-1 (CloudFront-compatible)
resource "aws_acm_certificate" "frontend_cert" {
  provider          = aws.global
  domain_name       = var.domain_name
  validation_method = "DNS"

  tags = {
    Project = var.project
  }
  lifecycle {
    prevent_destroy = true
  }
}

# Route 53 DNS validation record
resource "aws_route53_record" "cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.frontend_cert.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      type   = dvo.resource_record_type
      record = dvo.resource_record_value
    }
  }

  zone_id = var.route53_zone_id
  name    = each.value.name
  type    = each.value.type
  ttl     = 60
  records = [each.value.record]
}

# ACM Certificate Validation Resource
resource "aws_acm_certificate_validation" "cert_valid" {
  provider                = aws.global
  certificate_arn         = aws_acm_certificate.frontend_cert.arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]
}

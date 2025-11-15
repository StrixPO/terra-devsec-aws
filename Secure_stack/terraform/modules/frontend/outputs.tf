output "cloudfront_arn" {
  value = aws_cloudfront_distribution.frontend.arn
}

output "cf_domain_name" {
  value = aws_cloudfront_distribution.frontend.domain_name
}

output "cf_zone_id" {
  value = aws_cloudfront_distribution.frontend.hosted_zone_id
}
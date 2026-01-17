# Used to build the correct CloudTrail S3 path (AWSLogs/<account_id>/...)
data "aws_caller_identity" "current" {}

# CloudTrail logs bucket:
# - versioning: preserves audit history
# - prevent_destroy: protects logs from accidental deletion (audit integrity)
# - SSE-S3: baseline encryption at rest (consider SSE-KMS if you want key policy controls)
resource "aws_s3_bucket" "trail_logs" {
  bucket = "${var.project}-trail-logs"

  lifecycle {
    prevent_destroy = true
  }

  versioning {
    enabled = true
  }

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }

  tags = {
    Name = "${var.project}-trail-logs"
  }
}

# Block all public access. Audit logs must never be public.
resource "aws_s3_bucket_public_access_block" "trail_logs" {
  bucket = aws_s3_bucket.trail_logs.id

  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = true
  restrict_public_buckets = true
}

# Least-privilege policy:
# - CloudTrail can check bucket ACL
# - CloudTrail can write logs only under the AWSLogs/<account_id>/ prefix
resource "aws_s3_bucket_policy" "trail_logs_policy" {
  bucket = aws_s3_bucket.trail_logs.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Sid       = "AWSCloudTrailAclCheck",
        Effect    = "Allow",
        Principal = { Service = "cloudtrail.amazonaws.com" },
        Action    = "s3:GetBucketAcl",
        Resource  = aws_s3_bucket.trail_logs.arn
      },
      {
        Sid       = "AWSCloudTrailWrite",
        Effect    = "Allow",
        Principal = { Service = "cloudtrail.amazonaws.com" },
        Action    = "s3:PutObject",
        Resource  = "${aws_s3_bucket.trail_logs.arn}/AWSLogs/${data.aws_caller_identity.current.account_id}/*",
        Condition = {
          StringEquals = { "s3:x-amz-acl" = "bucket-owner-full-control" }
        }
      }
    ]
  })
}

# CloudTrail:
# - multi-region: captures activity across regions
# - include_global_service_events: includes IAM, STS, etc.
# - log file validation: detects tampering of delivered logs
resource "aws_cloudtrail" "main" {
  name                          = "${var.project}-trail"
  s3_bucket_name                = aws_s3_bucket.trail_logs.id
  include_global_service_events = true
  is_multi_region_trail         = true
  enable_log_file_validation    = true

  # Captures both read and write API events, plus management events.
  event_selector {
    read_write_type           = "All"
    include_management_events = true
  }

  depends_on = [aws_s3_bucket_policy.trail_logs_policy]
}

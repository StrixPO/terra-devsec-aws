resource "aws_s3_bucket" "secure_paste" {
  bucket = "${var.project}-pastes-${random_id.bucket_suffix.hex}"
  force_destroy = true

  tags = {
    Name = "${var.project}-pastes"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "default" {
  bucket = aws_s3_bucket.secure_paste.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "random_id" "bucket_suffix" {
  byte_length = 4
}


###DYNAMODB#####################
resource "aws_dynamodb_table" "paste_metadata" {
  name         = "${var.project}-metadata"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "paste_id"

  attribute {
    name = "paste_id"
    type = "S"
  }

  ttl {
    attribute_name = "expiry"
    enabled        = true
  }

  tags = {
    Name = "${var.project}-paste-metadata"
  }
}


#######IAM ROLE###################
data "aws_iam_policy_document" "secure_paste_policy" {
  statement {
    actions = [
      "s3:PutObject",
      "s3:GetObject",
      "s3:DeleteObject"
    ]
    resources = ["${aws_s3_bucket.secure_paste.arn}/*"]
  }

  statement {
    actions = [
      "dynamodb:PutItem",
      "dynamodb:GetItem",
      "dynamodb:DeleteItem",
      "dynamodb:Query"
    ]
    resources = [aws_dynamodb_table.paste_metadata.arn]
  }
}

resource "aws_iam_policy" "secure_paste_access" {
  name   = "${var.project}-paste-access"
  policy = data.aws_iam_policy_document.secure_paste_policy.json
}


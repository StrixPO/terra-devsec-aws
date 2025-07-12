
resource "aws_s3_bucket" "tf_state" {
  bucket        = "psstbin-tf-remote-state"
  force_destroy = true

  versioning {
    enabled = true
  }

  tags = {
    Name = "Terraform State Bucket"
  }
}

resource "aws_dynamodb_table" "tf_lock" {
  name         = "psstbin-tf-locks"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  tags = {
    Name = "Terraform Lock Table"
  }
}

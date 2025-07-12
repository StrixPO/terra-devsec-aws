terraform {
  backend "s3" {
    bucket         = "psstbin-tf-remote-state"
    key            = "psstbin/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "psstbin-tf-locks"
    encrypt        = true
  }
}

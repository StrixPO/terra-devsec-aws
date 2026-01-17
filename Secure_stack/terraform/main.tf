terraform {
  backend "s3" {
    bucket         = "psstbin-tf-state-hidden"
    key            = "securepaste/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "psstbin-tf-lock-hidden"
    encrypt        = true
  }
}


module "storage" {
  source  = "./modules/storage"
  project = var.project

}



module "app-lambda_create" {
  source             = "./modules/app-lambda/create"
  project            = var.project
  region             = var.aws_region
  create_zip_path    = var.create_zip_path
  bucket_name        = module.storage.bucket_name
  table_name         = module.storage.table_name
  dynamodb_table_arn = module.storage.dynamodb_table_arn
  bucket_arn         = module.storage.bucket_arn
}

module "app_lambda_get" {
  project                  = var.project
  source                   = "./modules/app-lambda/get"
  bucket_name              = module.storage.bucket_name
  table_name               = module.storage.table_name
  api_id                   = module.app-lambda_create.api_id
  get_zip_path             = var.get_zip_path
  api_execution_arn        = module.app-lambda_create.execute_arn
  lambda_exec_arn          = module.app-lambda_create.lambda_exec_arn
  lambda_exec_name         = module.app-lambda_create.lambda_exec_name
  lambda_access_policy_arn = module.app-lambda_create.lambda_access_policy_arn


}

module "frontend" {
  source             = "./modules/frontend"
  project            = var.project
  custom_domain      = var.custom_domain
  cloudflare_zone_id = var.cloudflare_zone_id
}



module "logging" {
  source           = "./modules/logging"
  project          = var.project
  lambda_name      = module.app-lambda_create.lambda_name
  enable_guardduty = false # Turn off to prevent creation
  sns_endpoint_email = var.sns_endpoint_email

}

module "cloudflare" {
  source = "./modules/cloudflare"

  cloudflare_zone_id   = var.cloudflare_zone_id
  cloudflare_api_token = var.cloudflare_api_token
  frontend_domain_name = module.frontend.cf_domain_name
}


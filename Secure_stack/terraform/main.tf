module "vpc" {
  source          = "./modules/vpc"
  project         = var.project
  vpc_cidr        = var.vpc_cidr
  public_subnets  = var.public_subnets
  private_subnets = var.private_subnets
  nat_instance_id = module.nat-instance.nat_instance_id
  azs             = var.azs
}

module "nat-instance" {
  source           = "./modules/nat-instance"
  project          = var.project
  nat_ami_id       = var.nat_ami_id
  key_name         = var.key_name
  public_subnet_id = module.vpc.public_subnets[0]
  private_subnets  = module.vpc.private_subnets
  vpc_id           = module.vpc.vpc_id
}

module "app" {
  source        = "./modules/app"
  project       = var.project
  vpc_id        = module.vpc.vpc_id
  key_name      = var.key_name
  subnet_id     = module.vpc.private_subnets[0]
  app_ami_id    = var.nat_ami_id
  bastion_sg_id = module.bastion.bastion_sg_id
  execution_arn = module.app-lambda_create.execution_arn
}

module "bastion" {
  source    = "./modules/bastion"
  ami_id    = var.ami_id
  key_name  = var.key_name
  vpc_id    = module.vpc.vpc_id
  subnet_id = module.vpc.public_subnets[0]
  project   = var.project
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
  project            = var.project
  source            = "./modules/app-lambda/get"
  bucket_name        = module.storage.bucket_name
  table_name         = module.storage.table_name
  api_id            = module.app-lambda_create.api_id
  get_zip_path    = var.get_zip_path
  api_execution_arn = module.app-lambda_create.execute_arn
  lambda_exec_arn = module.app-lambda_create.lambda_exec_arn
  lambda_exec_name         = module.app-lambda_create.lambda_exec_name
  lambda_access_policy_arn = module.app-lambda_create.lambda_access_policy_arn
  

}

module "frontend" {
  source  = "./modules/frontend"
  project = var.project
}


module "logging" {
  source      = "./modules/logging"
  project     = var.project
  lambda_name = module.app-lambda_create.lambda_name
}


output "bastion_ssh" {
  value = "ssh -i ${var.key_path} ec2-user@${module.bastion.bastion_public_ip}"
}


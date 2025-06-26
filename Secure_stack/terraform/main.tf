module "vpc" {
  source          = "./modules/vpc"
  project         = var.project
  vpc_cidr        = var.vpc_cidr
  public_subnets  = var.public_subnets
  private_subnets = var.private_subnets
  nat_instance_id    = module.nat-instance.nat_instance_id
  azs             = var.azs
}

module "nat-instance" {
    source = "./modules/nat-instance"
      project         = var.project
      nat_ami_id         = var.nat_ami_id
      key_name           = var.key_name
      public_subnet_id   = module.vpc.public_subnets[0]
      private_subnets   = module.vpc.private_subnets
      vpc_id             = module.vpc.vpc_id
}

module "app" {
    source = "./modules/app"
    project = var.project
    vpc_id  = module.vpc.vpc_id
    key_name           = var.key_name
    subnet_id   = module.vpc.private_subnets[0]
    app_ami_id = var.nat_ami_id
    bastion_sg_id    = module.bastion.bastion_sg_id
}

module "bastion" {
  source     = "./modules/bastion"
  ami_id     = var.ami_id
  key_name   = var.key_name
  vpc_id     = module.vpc.vpc_id
  subnet_id  = module.vpc.public_subnets[0]
  project    = var.project
}

module "storage" {
  source = "./modules/storage"
  project = var.project

}

resource "aws_iam_role_policy_attachment" "paste_access" {
  role       = module.app.secure_app_role_name 
  policy_arn = module.storage.secure_paste_policy_arn
}

output "bastion_ssh" {
  value = "ssh -i ${var.key_path} ec2-user@${module.bastion.bastion_public_ip}"
}

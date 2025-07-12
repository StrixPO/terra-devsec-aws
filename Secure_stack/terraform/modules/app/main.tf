resource "aws_instance" "secure_app" {
  ami           = var.app_ami_id
  instance_type = "t2.micro"
  subnet_id = var.subnet_id
  key_name      = var.key_name

  vpc_security_group_ids = [aws_security_group.app_sg.id]

  iam_instance_profile = aws_iam_instance_profile.secure_app_profile.name

  tags = {
    Name = "${var.project}-secure-app"
  }
}

resource "aws_security_group" "app_sg" {
  name        = "${var.project}-app-sg"
  description = "App server SG"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 22
    to_port         = 22
    protocol        = "tcp"
    security_groups = [var.bastion_sg_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_iam_role" "secure_app_role" {
  name = "${var.project}-app-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Principal = {
        Service = "ec2.amazonaws.com"
      },
      Action = "sts:AssumeRole"
    }]
  })
}


resource "aws_iam_instance_profile" "secure_app_profile" {
  name = "${var.project}-app-instance-profile1"
  role = aws_iam_role.secure_app_role.name
}


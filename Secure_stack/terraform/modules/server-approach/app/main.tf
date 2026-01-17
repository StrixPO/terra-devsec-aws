# -----------------------------------------------------------------------------
# EC2 (Optional / Non-core)
# -----------------------------------------------------------------------------
# NOTE:
# This instance is *not* required for the serverless paste flow.
# If you keep it, document the purpose clearly (e.g., bastion tooling, admin ops).
# Otherwise, delete it to keep the architecture narrative clean.
resource "aws_instance" "secure_app" {
  ami           = var.app_ami_id
  instance_type = "t2.micro" # cost-friendly; not suitable for production workloads
  subnet_id     = var.subnet_id
  key_name      = var.key_name

  # Restrict inbound via a bastion SG; do not open SSH to the world.
  vpc_security_group_ids = [aws_security_group.app_sg.id]

  # Attach an IAM role via instance profile for AWS API access.
  # SECURITY NOTE: keep role permissions minimal; prefer SSM over SSH long-term.
  iam_instance_profile = aws_iam_instance_profile.secure_app_profile.name

  tags = {
    Name = "${var.project}-secure-app"
  }
}

resource "aws_security_group" "app_sg" {
  name        = "${var.project}-app-sg"
  description = "App server SG (SSH only from bastion)"
  vpc_id      = var.vpc_id

  # SSH only from a trusted bastion security group (not CIDR-based).
  ingress {
    from_port       = 22
    to_port         = 22
    protocol        = "tcp"
    security_groups = [var.bastion_sg_id]
  }

  # Egress open to the internet.
  # SECURITY NOTE: if this instance doesn't need outbound to anywhere, restrict it.
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# IAM role assumed by EC2
resource "aws_iam_role" "secure_app_role" {
  name = "${var.project}-app-role"

  # Trust policy: allow EC2 to assume this role.
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Principal = { Service = "ec2.amazonaws.com" },
      Action = "sts:AssumeRole"
    }]
  })
}

# Instance profile is how EC2 actually attaches the role.
resource "aws_iam_instance_profile" "secure_app_profile" {
  name = "${var.project}-app-instance-profile-4"
  role = aws_iam_role.secure_app_role.name
}

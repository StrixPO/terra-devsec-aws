# Deployment Guide

Complete step-by-step guide to deploy PsstBin to your own AWS account.

## Prerequisites

### Required Tools

- **AWS CLI** (v2+)

```bash
  aws --version
  # If not installed: https://aws.amazon.com/cli/
```

- **Terraform** (v1.0+)

```bash
  terraform --version
  # If not installed: https://www.terraform.io/downloads
```

- **Cloudflare Account** (free tier works)
  - Domain registered (or use Cloudflare Registrar)
  - Zone created for your domain

### AWS Setup

1. **Create AWS Account** (if you don't have one)
   - https://aws.amazon.com

2. **Create IAM User** with permissions:
   - Lambda full access
   - S3 full access
   - DynamoDB full access
   - CloudFront full access
   - API Gateway full access
   - IAM (for creating roles)
   - ACM (for SSL certificates)

3. **Configure AWS CLI**

```bash
   aws configure
   # Enter your Access Key ID
   # Enter your Secret Access Key
   # Region: us-east-1 (or your preferred region)
   # Output: json
```

### Cloudflare Setup

1. **Get Zone ID**
   - Log into Cloudflare Dashboard
   - Select your domain
   - Scroll down → Zone ID (copy this)

2. **Create API Token**
   - My Profile → API Tokens → Create Token
   - Use template: "Edit zone DNS"
   - Zone Resources: Include → Specific zone → Your domain
   - Copy the token (you won't see it again!)

## Step-by-Step Deployment

### 1. Clone Repository

```bash
git clone https://github.com/StrixPO/terra-devsec-aws.git
cd psstbin
```

### 2. Prepare Lambda Functions

```bash
# Create Lambda package for 'create' function
cd lambda/create
zip -r ../../lambda_create.zip .

# Create Lambda package for 'get' function
cd ../get
zip -r ../../lambda_get.zip .

cd ../..
```

### 3. Configure Terraform

```bash
cd terraform

# Copy example variables
cp terraform.tfvars.example terraform.tfvars

# Edit with your values
nano terraform.tfvars  # or vim, code, etc.
```

**Edit terraform.tfvars:**

```hcl
aws_region = "us-east-1"
project = "psstbin"  # Change if you want

cloudflare_zone_id   = "abc123..."  # From Cloudflare dashboard
cloudflare_api_token = "xyz789..."  # Your API token

# Your domain
custom_domain = "psstbin.com"  # Or subdomain: paste.yourdomain.com

# Lambda paths (should be correct already)
create_zip_path = "../lambda_create.zip"
get_zip_path    = "../lambda_get.zip"
```

### 4. Initialize Terraform

```bash
terraform init
```

**Expected output:**

```
Initializing modules...
Initializing the backend...
Terraform has been successfully initialized!
```

### 5. Plan Deployment

```bash
terraform plan
```

Review the resources that will be created:

- S3 buckets (2): frontend + pastes
- DynamoDB table
- Lambda functions (2): create + get
- API Gateway
- CloudFront distribution
- ACM certificate
- Cloudflare DNS records
- IAM roles and policies

### 6. Deploy Infrastructure

```bash
terraform apply
```

Type `yes` when prompted.

**This takes 15-20 minutes** (CloudFront distribution is slow to create)

### 7. Get API Gateway URL

```bash
terraform output api_gateway_url
```

Copy this URL (looks like: `https://abc123.execute-api.us-east-1.amazonaws.com`)

### 8. Update Frontend

Edit `frontend/script.js`:

```javascript
// Change this line:
const API = "https://YOUR-API-URL-HERE";

// To your actual API URL:
const API = "https://abc123.execute-api.us-east-1.amazonaws.com";
```

### 9. Upload Frontend to S3

```bash
# Get your S3 bucket name
terraform output  # Look for frontend_bucket_name

# Upload files
aws s3 sync ../frontend s3://psstbin-frontend/ --exclude ".git/*"
```

### 10. Get CloudFront Distribution ID

```bash
terraform output  # Look for cloudfront_distribution_id
# Or:
aws cloudfront list-distributions --query "DistributionList.Items[?Comment=='psstbin-frontend'].Id" --output text
```

### 11. Invalidate CloudFront Cache

```bash
aws cloudfront create-invalidation \
  --distribution-id YOUR_DIST_ID \
  --paths "/*"
```

### 12. Test Your Deployment

1. **Visit your domain:** https://psstbin.com
2. **Create a test paste** (without encryption)
3. **Retrieve it** using the paste ID
4. **Create encrypted paste** with password
5. **Retrieve encrypted paste** and enter password

## Troubleshooting

### "Access Denied" on website

**Problem:** CloudFront can't access S3 bucket

**Solution:**

```bash
# Check S3 bucket policy
aws s3api get-bucket-policy --bucket psstbin-frontend

# If missing, reapply Terraform
terraform apply -target=aws_s3_bucket_policy.frontend
```

### API returns 500 errors

**Problem:** Lambda can't access S3 or DynamoDB

**Solution:**

```bash
# Check Lambda logs
aws logs tail /aws/lambda/psstbin-paste-create --follow

# Common fix: Reapply IAM policies
terraform apply -target=module.app-lambda_create.aws_iam_policy.lambda_access
```

### Certificate validation stuck

**Problem:** ACM certificate waiting for DNS validation

**Solution:**

- Check Cloudflare DNS records exist
- Wait 10-20 minutes (DNS propagation)
- Verify CNAME records in Cloudflare dashboard

### "Paste already viewed" on first try

**Problem:** Caching issue or Lambda bug

**Solution:**

- Clear browser cache
- Wait 60 seconds and try again
- Check Lambda logs for errors

## Cost Monitoring

Set up a billing alarm:

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name psstbin-budget \
  --alarm-description "Alert if PsstBin costs exceed $10/month" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 86400 \
  --evaluation-periods 1 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=Currency,Value=USD
```

## Updating the Application

### Update Lambda Code

```bash
# 1. Make changes to lambda_function.py
# 2. Re-zip
cd lambda/create
zip -r ../../lambda_create.zip .

# 3. Reapply Terraform
cd ../../terraform
terraform apply -target=module.app-lambda_create.aws_lambda_function.paste_create
```

### Update Frontend

```bash
# 1. Make changes to HTML/CSS/JS
# 2. Upload to S3
aws s3 sync ../frontend s3://psstbin-frontend/

# 3. Invalidate cache
aws cloudfront create-invalidation --distribution-id YOUR_ID --paths "/*"
```

## Destroying Everything

**⚠️ Warning:** This deletes all data permanently!

```bash
cd terraform
terraform destroy
```

Type `yes` when prompted.

**Note:** You may need to:

1. Empty S3 buckets manually first
2. Delete CloudWatch log groups manually

## Next Steps

- [ ] Set up monitoring (CloudWatch dashboards)
- [ ] Configure budget alerts
- [ ] Set up automated backups (if needed)
- [ ] Add custom error pages
- [ ] Set up WAF (if you get abuse)

## Getting Help

- **GitHub Issues:** https://github.com/yourusername/psstbin/issues
- **Terraform Docs:** https://registry.terraform.io/providers/hashicorp/aws/latest/docs
- **AWS Support:** https://console.aws.amazon.com/support/

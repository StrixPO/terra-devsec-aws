# 🔐 PsstBin

End-to-end encrypted pastebin with burn-after-reading and automatic secret detection.

**Live Demo:** [psstbin.com](https://psstbin.com)

![PsstBin Architecture](docs/architecture.png) <!-- We'll create this -->

## ✨ Features

- 🔐 **Client-side encryption** - AES-256-GCM encryption in your browser (zero-knowledge)
- 🔥 **Burn after reading** - Pastes self-destruct after first view
- 🚨 **Secret detection** - Automatically detects AWS keys, tokens, and credentials
- ⏰ **Auto-expiry** - Configurable from 5 minutes to 7 days
- 📦 **Serverless** - Fully serverless AWS architecture
- 🏗️ **Infrastructure as Code** - Complete Terraform deployment
- 💰 **Cost-effective** - Runs for ~$3-5/month on AWS

## 🎯 Use Cases

- Share credentials with team members securely
- Send sensitive data without leaving traces
- Share temporary access tokens
- Prevent accidental credential leaks (secret detection warns you)
- Share encrypted code snippets

## 🏗️ Architecture

```
┌─────────────┐
│   Browser   │ ← AES-256-GCM Encryption
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ CloudFront  │ ← CDN + Custom Domain
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ API Gateway │ ← Rate Limiting
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Lambda    │ ← Secret Detection
└──────┬──────┘
       │
       ├──────► S3 (encrypted storage)
       │
       └──────► DynamoDB (metadata + TTL)
```

**Key Security Features:**

- Server never sees decryption key (client-side encryption)
- Pastes are destroyed after viewing (one-time use)
- Automatic TTL cleanup (DynamoDB + S3 lifecycle)
- Server-side encryption at rest (SSE-S3)

## 🚀 Quick Start

### Prerequisites

- AWS Account
- Terraform >= 1.0
- AWS CLI configured
- Cloudflare account (for domain + DNS)

### Deployment

1. **Clone the repository**

```bash
   git clone https://github.com/yourusername/psstbin.git
   cd psstbin
```

2. **Configure variables**

```bash
   cd terraform
   cp terraform.tfvars.example terraform.tfvars
   # Edit terraform.tfvars with your values
```

3. **Deploy infrastructure**

```bash
   terraform init
   terraform plan
   terraform apply
```

4. **Upload frontend**

```bash
   # Get your S3 bucket name from Terraform output
   aws s3 sync ../frontend s3://YOUR-BUCKET-NAME/

   # Invalidate CloudFront cache
   aws cloudfront create-invalidation \
     --distribution-id YOUR-DIST-ID \
     --paths "/*"
```

5. **Update frontend API URL**

```bash
   # Get your API Gateway URL from Terraform output
   terraform output api_gateway_url

   # Update frontend/script.js
   # Change: const API = "https://YOUR-API-URL"
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions.

## 📊 Cost Breakdown

Based on moderate usage (1000 pastes/month):

| Service     | Cost/Month       |
| ----------- | ---------------- |
| Lambda      | $0.20            |
| DynamoDB    | $0.50            |
| S3          | $0.50            |
| CloudFront  | $1.00            |
| API Gateway | $1.00            |
| **Total**   | **~$3.20/month** |

Within AWS Free Tier: ~$0-1/month for first 12 months

## 🔒 Security

### Client-Side Encryption

- **Algorithm:** AES-256-GCM
- **Key Derivation:** PBKDF2 (100,000 iterations, SHA-256)
- **Salt:** 16 bytes (random per paste)
- **IV:** 12 bytes (random per paste)

### Secret Detection Patterns

Automatically detects:

- AWS Access Keys (AKIA...)
- Private SSH/SSL Keys
- GitHub Personal Access Tokens
- Google API Keys
- JWT Tokens
- Azure GUIDs (with context checking)
- GCP Service Account Keys
- Password/Secret patterns in code

### Data Lifecycle

1. Paste created → Stored with TTL
2. First view → Marked as "used", content returned
3. Second view attempt → 410 Gone
4. Expiry time → DynamoDB deletes (within 48 hours)
5. S3 lifecycle → Deletes after 2 days (safety net)

## 🛠️ Tech Stack

**Frontend:**

- Vanilla JavaScript (Web Crypto API)
- HTML5 + CSS3
- No frameworks (lightweight, <10KB)

**Backend:**

- AWS Lambda (Python 3.12)
- API Gateway (HTTP API)
- DynamoDB (with TTL)
- S3 (with lifecycle policies)
- CloudFront (CDN)

**Infrastructure:**

- Terraform (IaC)
- Cloudflare (DNS + SSL)

## 📁 Project Structure

```
psstbin/
├── frontend/
│   ├── index.html
│   ├── script.js
│   └── styles.css
├── terraform/
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── modules/
│   │   ├── storage/
│   │   ├── app-lambda/
│   │   ├── frontend/
│   │   └── cloudflare/
│   └── terraform.tfvars.example
├── lambda/
│   ├── create/
│   │   └── lambda_function.py
│   └── get/
│       └── lambda_function.py
├── docs/
│   └── architecture.png
├── README.md
├── DEPLOYMENT.md
├── ARCHITECTURE.md
├── LICENSE
└── .gitignore
```

## 🤝 Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

**Areas for improvement:**

- [ ] CLI tool for paste creation
- [ ] Browser extension
- [ ] Syntax highlighting
- [ ] File upload support
- [ ] Custom paste IDs
- [ ] QR code generation
- [ ] Rate limiting per IP
- [ ] Admin dashboard

## 📝 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- Inspired by [PrivateBin](https://privatebin.info/)
- Built as a learning project for serverless architecture
- Thanks to the r/selfhosted community for feedback

## 📧 Contact

- GitHub Issues: [Report bugs or request features](https://github.com/yourusername/psstbin/issues)
- Author: Your Name
- Website: [yourwebsite.com](https://yourwebsite.com)

---

**⚠️ Disclaimer:** This is a hobby project. While it implements strong encryption, it's not audited. Use at your own risk for production secrets. For enterprise use, consider proper secret management tools like HashiCorp Vault or AWS Secrets Manager.

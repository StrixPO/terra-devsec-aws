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

## 🔐 Security Model

PsstBin is designed as an **ephemeral, privacy-first pastebin** with explicit security tradeoffs.  
It supports **two privacy modes** to balance confidentiality, usability, and safety.

---

### Privacy Modes

#### 1) Encrypted Mode (Default – Zero-Knowledge)
- Paste content is **encrypted in the browser before upload** (AES-GCM).
- The backend **never sees plaintext** and treats content as opaque ciphertext.
- Only **non-secret metadata** is stored server-side:
  - expiry timestamp (TTL)
  - one-time-read flag
  - encryption metadata (salt, IV)
- **Encryption keys are never transmitted or stored** on the server.

> In this mode, the system is **zero-knowledge by design**: compromise of backend infrastructure does not expose paste contents.

---

#### 2) Plaintext Mode (Optional – UX Warnings)
- Paste content is uploaded **unencrypted**.
- The backend runs **best-effort secret detection** (regex + heuristics) to identify:
  - cloud credentials
  - API keys
  - private keys
  - tokens (GitHub, JWT, GCP, etc.)
- Only **secret categories** are recorded (not values).
- If potential secrets are detected, the user receives a **warning encouraging encryption**.

> Secret detection is **not a security boundary**.  
> False positives and negatives are expected. This feature exists solely as a safety nudge.

---

### Threat Model

#### What PsstBin Protects Against
- Accidental disclosure via long-lived or reused paste URLs
- Backend compromise exposing stored data
- Passive infrastructure-level data access
- Enumeration attacks via non-guessable paste IDs
- Over-retention of sensitive data (via TTL enforcement)

#### What PsstBin Does **Not** Protect Against
- Compromised client devices or browsers
- Malicious browser extensions
- Link sharing outside trusted channels
- Users choosing plaintext mode for sensitive data
- Weak or reused passphrases (if used)

---

### Storage & Data Lifecycle

- **Small pastes** are stored inline in DynamoDB.
- **Large pastes** are stored in S3 with server-side encryption (SSE-S3).
- All pastes have a **hard TTL** (5 minutes – 7 days).
- One-time read semantics ensure pastes are invalidated after retrieval.
- Deletion is best-effort and enforced via DynamoDB TTL + lifecycle policies.

---

### Defense in Depth

- Strict paste ID validation (non-enumerable, length-limited).
- API Gateway throttling to reduce abuse and cost amplification.
- No sensitive content is logged (plaintext or ciphertext).
- Encryption at rest is treated as **defense-in-depth**, not a trust boundary.

---

### Design Philosophy

PsstBin intentionally avoids claiming “perfect security.”

Instead, it focuses on:
- **Explicit trust boundaries**
- **Short data lifetimes**
- **Client-side confidentiality by default**
- **Clear tradeoffs over hidden behavior**

Security features are implemented to reduce *realistic risk*, not to check buzzword boxes.


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


# PsstBin

#### Encrypted. Ephemeral. Yours.

PsstBin is a cloud-native, serverless pastebin designed for zero-trust sharing of sensitive content. With client-side encryption, one-time access, and DevSecOps at its core, PsstBin is ideal for developers, security engineers, and privacy-conscious users who want more than just a public pastebin.

### 🔐 Features

- Client-side AES-GCM encryption (browser-based, zero-trust)

- One-time access with automatic deletion

- Secret detection using pattern matching

- Time-limited pastes (default: 1 hour)

- Burn-after-read enforcement

- WAF protections and rate limiting

- CLI tool for quick paste sharing

- Monitoring via CloudTrail, CloudWatch, GuardDuty

### Architecture

- Frontend: Static HTML/JS (optional client-side crypto)

- API: AWS API Gateway + Lambda (Python)

- Storage: DynamoDB (small text) or S3 (large/encoded text)

- Encryption: Client-side (AES-GCM via WebCrypto) + optional S3 KMS

- Security: IAM (least privilege), WAF, budget alerts

### Getting Started

### CLI Usage

Create a paste
`psstbin create --text "my secret" --encrypt`

Get a paste
`psstbin get <paste_id>`

Check paste metadata
`psstbin status <paste_id>`

Deploy Your Own (Terraform)

```
cd terraform
terraform init
terraform apply
```

### Tech Stack

- AWS: Lambda, API Gateway, S3, DynamoDB, WAFv2, CloudTrail, CloudWatch

- IaC: Terraform (modular)

- CLI: Python + Click

- Frontend: HTML/CSS/JS (AES-GCM via WebCrypto)

### Security Highlights

- Zero-trust: Decryption only possible with client-supplied key

- No public paste listing

- Server knows nothing of encrypted content

- Paste cannot be viewed more than once

- IAM permissions hardened

- No hardcoded secrets

- For more, see SECURITY.md

### Limitations & Future Work

- No authentication yet (optional anonymous model)

- No paste previews or history

- No expiration refresh/update

- CLI-only unless hosted via HTTPS for frontend

### Threat Model

Threat Mitigation
API scraping WAF rate limits + secret detection

Replay/Reuse One-time paste destruction

Cloud compromise Client-side encryption + IAM restrictions

Leak through logs No logging of content bodies

### License

MIT © 2025 Rusar

## Acknowledgements

Built with 💻, ☕, and a lot of terraform destroy.

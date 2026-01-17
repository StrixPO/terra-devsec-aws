# 🔐 Security Policy

## 📣 Reporting a Vulnerability

We take security seriously.

If you discover a vulnerability or have a security concern, please **do not open a public GitHub issue**. Instead, report it **privately** to the maintainer at:

📧 `wrkrusar@gmail.com`  
✉️ (Or use GitHub's private vulnerability reporting feature)

We will respond within **3 working days** and aim to patch verified issues within **7 days** of triage.

---

## 🛡️ Project Security Principles

PsstBin was built from the ground up with **DevSecOps and zero-trust** principles. Key tenets include:

- **Client-side encryption (optional):** Sensitive content never touches the backend in plaintext if encrypted.
- **One-time access (burn-after-read):** Pastes are destroyed after retrieval to minimize exposure.
- **Serverless + ephemeral:** No long-running infrastructure; no unnecessary open ports.
- **Secrets detection & alerting:** AWS Lambda scans for patterns like API keys or credentials.
- **WAF protection:** API Gateway is shielded by AWS WAF with OWASP rules and rate-limiting.
- **Minimal IAM roles:** Follows least-privilege access for Lambda, S3, and DynamoDB.

---

## 🧠 Threat Model Summary

| Threat                             | Mitigation Strategy                          |
| ---------------------------------- | -------------------------------------------- |
| Unauthorized access to stored data | S3 encryption + optional client-side AES-GCM |
| Replay attacks                     | One-time use design (used flag)              |
| Secret leakage (e.g., API keys)    | Secret scanning + CloudWatch alerts          |
| Injection or malformed input       | Lambda input validation, no dynamic eval     |
| Brute-force or enumeration attacks | WAF rate limits + UUID fallback              |
| Insider misconfiguration           | Terraform IaC + CloudTrail logging           |

---

## 🧬 Dependency Management

- **Lambda:** Python 3.x, Boto3 (no third-party deps by default)
- **CLI:** `requests`, `click`, `.env` (no known CVEs in pinned versions)
- **Frontend:** Pure HTML/JS/CSS, using WebCrypto only

No CDN libraries or unverified packages are used in production.

---

## 🔒 Boundary of Responsibility

This project ensures secure **transit**, **storage**, and **ephemeral access**. However:

> 🔸 **We cannot decrypt user data** if client-side encryption is used — lost passwords mean lost data.  
> 🔸 End-users must ensure their devices and browsers are secure when using the frontend.  
> 🔸 We do not store logs of paste content.

---

## 🔍 Security Testing & Auditing Tools

- [x] AWS WAF (OWASP top 10)
- [x] AWS CloudTrail + GuardDuty
- [x] `tfsec`, `checkov` for Terraform code
- [x] GitHub Actions CI + vulnerability scanning
- [x] IAM access analyzer (manual reviews)

---

## 📜 License & Legal

This project is open-source under the [MIT License](./LICENSE.md).  
No warranty is provided. Use at your own risk.

---

Thanks for helping make PsstBin more secure 🙏


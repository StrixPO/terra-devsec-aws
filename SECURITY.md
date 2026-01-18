# 🔐 Security Policy

This document describes how to responsibly report security issues in **PsstBin**,  
and outlines the project’s security boundaries and guarantees.

---

## 📣 Reporting a Vulnerability

If you discover a security vulnerability or have a responsible disclosure:

- **Do not open a public GitHub issue**
- Report privately via:
  - 📧 Email: `wrkrusar@gmail.com`
  - ✉️ GitHub’s **Private Vulnerability Reporting**

### Response Targets
- Initial response: **within 3 business days**
- Verified issue triage: **within 7 days**

We appreciate responsible disclosure and coordinated fixes.

---

## 🛡️ Security Scope & Principles

PsstBin is an **ephemeral, serverless pastebin** designed with the following principles:

- **Short-lived data by default** (mandatory TTL)
- **Client-side encryption support** (zero-knowledge mode)
- **Minimal backend trust**
- **Explicit security tradeoffs**

Security features are implemented to reduce realistic risk, not to guarantee absolute secrecy.

---

## 🔐 Data Handling Modes

### Encrypted Mode (Default)
- Paste content is **encrypted in the browser** before upload.
- The backend stores **only ciphertext and non-secret metadata**.
- Encryption keys are **never transmitted or stored**.
- In this mode, the backend **cannot inspect, scan, or decrypt content**.

### Plaintext Mode (Optional)
- Paste content is uploaded unencrypted.
- Backend performs **best-effort secret detection** (regex + heuristics).
- Only **secret categories** are recorded (never raw values).
- Used solely to **warn users** and encourage encryption.

> Secret detection is a **UX warning mechanism**, not a security boundary.

---

## 🧠 Threat Model Summary

| Threat                          | Mitigation                                      |
|---------------------------------|-------------------------------------------------|
| Backend data exposure           | Client-side encryption (encrypted mode)        |
| Long-lived data leakage         | Mandatory TTL + one-time read                  |
| Paste enumeration               | Non-guessable IDs + strict validation          |
| Accidental secret sharing       | Optional plaintext warnings                    |
| Oversized / abusive payloads    | Size limits + API Gateway throttling            |

---

## 🚫 Out of Scope / Non-Goals

PsstBin does **not** protect against:

- Compromised user devices or browsers
- Malicious browser extensions
- Shared paste URLs being forwarded
- Weak or reused passphrases
- Users choosing plaintext mode for sensitive data

---

## 🔍 Logging & Observability

- Paste **content is never logged** (plaintext or ciphertext).
- Logs are limited to metadata (sizes, flags, request flow).
- Infrastructure auditing relies on AWS-native tooling.

---

## 🔒 Boundary of Responsibility

- Users are responsible for safeguarding decryption keys and links.
- Lost keys or expired pastes **cannot be recovered**.
- PsstBin provides **no warranty** for data availability or persistence.

---

## 🧪 Security Testing & Hygiene

- Terraform IaC with manual IAM review
- Static validation of inputs
- Minimal third-party dependencies
- CI-based dependency and code scanning (where applicable)

This project has **not undergone a formal third-party security audit**.

---

## 📜 Legal

This project is released under the [MIT License](./LICENSE.md).  
Use at your own risk.

---

Thank you for helping improve PsstBin’s security posture 🙏

# Architecture Documentation

Technical deep-dive into PsstBin's architecture and design decisions.

## System Overview

PsstBin is a serverless application built entirely on AWS, with Cloudflare handling DNS and CDN proxying (optional).

### High-Level Architecture
```
┌──────────────────────────────────────────────────────────────┐
│                        User's Browser                         │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Web Crypto API (AES-256-GCM Encryption/Decryption)   │  │
│  └────────────────────────────────────────────────────────┘  │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                    Cloudflare (Optional)                      │
│             DNS Resolution + DDoS Protection                  │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                 Amazon CloudFront (CDN)                       │
│        Frontend Delivery + SSL/TLS Termination               │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                  Amazon S3 (Frontend Bucket)                  │
│            Static Files: HTML, CSS, JavaScript                │
└──────────────────────────────────────────────────────────────┘


                  ┌───────── API Requests ─────────┐
                  │                                  │
                  ▼                                  ▼
┌─────────────────────────────┐   ┌─────────────────────────────┐
│   API Gateway (HTTP API)    │   │   API Gateway (HTTP API)    │
│      POST /create           │   │      POST /paste            │
└──────────────┬──────────────┘   └──────────────┬──────────────┘
               │                                  │
               ▼                                  ▼
┌─────────────────────────────┐   ┌─────────────────────────────┐
│  Lambda: paste_create       │   │  Lambda: get_paste          │
│  - Validate input           │   │  - Fetch from DynamoDB      │
│  - Detect secrets           │   │  - Fetch from S3 (if large) │
│  - Store in DynamoDB/S3     │   │  - Mark as used             │
└──────────────┬──────────────┘   └──────────────┬──────────────┘
               │                                  │
               │                                  │
               ▼                                  ▼
      ┌─────────────────┐              ┌─────────────────┐
      │   DynamoDB      │◄─────────────┤   DynamoDB      │
      │   - Metadata    │              │   - Metadata    │
      │   - Small pastes│              │   - Small pastes│
      │   - TTL enabled │              │   - TTL enabled │
      └─────────────────┘              └─────────────────┘
               │
               ▼
      ┌─────────────────┐
      │   S3 (Pastes)   │
      │   - Large pastes│
      │   - SSE-AES256  │
      │   - Lifecycle:  │
      │     Delete 2d   │
      └─────────────────┘
```

## Data Flow

### Creating a Paste

**Without Encryption:**

1. User enters content in browser
2. Frontend validates (size check: 1MB max)
3. POST to `/create` with:
```json
   {
     "content": "plain text",
     "expiry_seconds": 3600,
     "content_encrypted": false
   }
```
4. Lambda `paste_create`:
   - Validates input
   - **Runs secret detection** on plaintext
   - Generates UUID if no paste_id provided
   - Calculates expiry timestamp
   - If content < 4KB: Stores in DynamoDB `content` field
   - If content > 4KB: Stores in S3, path in DynamoDB
5. Returns paste_id + warnings

**With Encryption:**

1. User enters content + password
2. Frontend encrypts:
   - Generates random salt (16 bytes)
   - Generates random IV (12 bytes)
   - Derives key with PBKDF2 (100k iterations)
   - Encrypts with AES-256-GCM
   - Encodes to base64
3. POST to `/create` with:
```json
   {
     "content": "base64_encrypted_data",
     "salt": "base64_salt",
     "iv": "base64_iv",
     "expiry_seconds": 3600,
     "content_encrypted": true
   }
```
4. Lambda `paste_create`:
   - Validates base64
   - **Skips secret detection** (can't detect in encrypted data)
   - Decodes base64 to bytes
   - If bytes < 4KB: Stores base64 string in DynamoDB
   - If bytes > 4KB: Stores bytes in S3
   - Stores salt + IV in DynamoDB

### Retrieving a Paste

**First View:**

1. Frontend: POST to `/paste` with `paste_id`
2. Lambda `get_paste`:
   - Fetches from DynamoDB
   - Checks if expired (compares `expiry` to current time)
   - Checks if already used (`used == true`)
   - If in DynamoDB `content` field: Returns directly
   - If in S3: Fetches from S3 bucket
   - **Marks paste as used** (`used = true`)
   - Returns: `{content, encrypted, salt?, iv?}`
3. Frontend:
   - If `encrypted == false`: Display immediately
   - If `encrypted == true`: Prompt for password, decrypt client-side

**Second View Attempt:**

1. POST to `/paste` with same `paste_id`
2. Lambda sees `used == true`
3. Returns `410 Gone: "Paste already viewed"`

## Storage Strategy

### DynamoDB Schema
```
paste_metadata (Table)
├── paste_id (String, Partition Key)
├── expiry (Number) - Unix timestamp
├── ttl (Number) - Unix timestamp (DynamoDB TTL attribute)
├── used (Boolean) - One-time flag
├── encrypted (Boolean) - Encryption flag
├── content (String, Optional) - If < 4KB
├── s3_key (String, Optional) - If >= 4KB
├── salt (String, Optional) - If encrypted
├── iv (String, Optional) - If encrypted
├── has_secrets (Boolean, Optional) - If secrets detected
└── secret_types (String, Optional) - Comma-separated list
```

### Size-Based Storage Decision
```python
MAX_INLINE_SIZE = 4096  # 4KB

if len(content_bytes) <= MAX_INLINE_SIZE:
    # Store in DynamoDB 'content' field
    item["content"] = {"S": content_str}
else:
    # Store in S3
    s3_key = f"pastes/{paste_id}.{ext}"
    item["s3_key"] = {"S": s3_key}
    s3.put_object(Bucket=bucket, Key=s3_key, Body=content_bytes)
```

**Rationale:**
- DynamoDB: Faster access, cheaper for small items
- S3: Cheaper for large items, better for binary data
- 4KB threshold: Balances cost and performance

### Data Lifecycle
```
T=0        Paste created
           ├─ stored in DynamoDB/S3
           ├─ TTL set to expiry timestamp
           └─ used = false

T=0 to T   Paste accessible
           └─ Can be viewed once

T (first)  Paste viewed
           ├─ content returned
           └─ used = true

T (second) Paste inaccessible
           └─ 410 Gone returned

T+expiry   DynamoDB TTL triggers
           └─ Item deleted (within 48 hours)

T+2 days   S3 Lifecycle Policy
           └─ Object deleted (safety net)
```

## Security Architecture

### Encryption Flow
```
┌──────────────────────────────────────────────────────┐
│                    User's Browser                     │
│                                                       │
│  1. User enters password: "mysecret123"              │
│                                                       │
│  2. Generate random salt (16 bytes)                  │
│     → e.g., 0x1a2b3c...                              │
│                                                       │
│  3. Generate random IV (12 bytes)                    │
│     → e.g., 0x9f8e7d...                              │
│                                                       │
│  4. Derive encryption key using PBKDF2:              │
│     key = PBKDF2(password, salt, 100000, SHA-256)    │
│                                                       │
│  5. Encrypt plaintext with AES-256-GCM:              │
│     ciphertext = AES_GCM_Encrypt(key, iv, plaintext) │
│                                                       │
│  6. Encode to Base64:                                │
│     content = base64(ciphertext)                     │
│     salt = base64(salt)                              │
│     iv = base64(iv)                                  │
│                                                       │
│  7. Send to server (password never sent!)            │
│     POST {content, salt, iv, encrypted: true}        │
└──────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────┐
│                     AWS Lambda                        │
│                                                       │
│  - Receives encrypted blob (base64)                  │
│  - Cannot decrypt (doesn't have password/key)        │
│  - Stores: ciphertext, salt, IV                      │
│  - Zero knowledge of plaintext                       │
└──────────────────────────────────────────────────────┘
```

### Secret Detection Patterns

Implemented regex patterns:

1. **AWS Access Keys:** `AKIA[0-9A-Z]{16}`
2. **Private Keys:** `-----BEGIN (RSA|EC|DSA)? PRIVATE KEY-----`
3. **GitHub PAT:** `gh[pousr]_[A-Za-z0-9_]{36}`
4. **Google API Key:** `AIza[0-9A-Za-z\-_]{35}`
5. **JWT Tokens:** `eyJ[A-Za-z0-9_-]+...`
6. **Password Patterns:** `password\s*[:=]\s*['"]...`
7. **Azure GUIDs** (with context checking)
8. **Docker Auth** (with entropy checking)

**False Positive Mitigation:**

- Placeholder detection (`password`, `secret`, `changeme`, `example`)
- Context checking (e.g., Azure GUID near `client_id` keyword)
- Entropy analysis (for base64-looking strings)

## Rate Limiting

### API Gateway Throttling
```hcl
default_route_settings {
  throttling_burst_limit = 50   # Max concurrent requests
  throttling_rate_limit  = 10   # Requests per second
}
```

**Behavior:**
- Allows bursts up to 50 requests
- Sustained rate: 10 req/sec per user
- Beyond limits: `429 Too Many Requests`

### Future Enhancements

- [ ] Per-IP rate limiting (requires WAF)
- [ ] CAPTCHA for suspicious activity
- [ ] Account-based quotas

## Cost Optimization

### Decisions Made

1. **HTTP API vs REST API**
   - Chose HTTP API (70% cheaper)
   - No caching needed (one-time pastes)

2. **DynamoDB On-Demand vs Provisioned**
   - On-demand for unpredictable traffic
   - Pay only for what you use

3. **S3 Lifecycle Policies**
   - Auto-delete after 2 days
   - Prevents forgotten pastes from accumulating cost

4. **CloudFront Caching**
   - Frontend: Cached (reduces S3 requests)
   - API: Not cached (dynamic content)

5. **Lambda Memory**
   - 128MB sufficient for text processing
   - Higher memory = higher cost, no benefit here

### Cost Per 1000 Pastes

| Operation | AWS Service | Cost |
|-----------|-------------|------|
| Create paste | Lambda invocation | $0.0002 |
| Create paste | DynamoDB write | $0.001 |
| Get paste | Lambda invocation | $0.0002 |
| Get paste | DynamoDB read | $0
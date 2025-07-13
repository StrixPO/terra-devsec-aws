const API = "https://drcgp111jb.execute-api.us-east-1.amazonaws.com";

// Utility: Convert base64 to ArrayBuffer
function base64ToArrayBuffer(base64) {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes.buffer;
}

// Utility: Convert ArrayBuffer to base64
function arrayBufferToBase64(buffer) {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  bytes.forEach((b) => (binary += String.fromCharCode(b)));
  return btoa(binary);
}

async function deriveKey(password, salt) {
  const enc = new TextEncoder();
  const keyMaterial = await window.crypto.subtle.importKey(
    "raw",
    enc.encode(password),
    "PBKDF2",
    false,
    ["deriveKey"]
  );
  return window.crypto.subtle.deriveKey(
    {
      name: "PBKDF2",
      salt: salt,
      iterations: 100000,
      hash: "SHA-256",
    },
    keyMaterial,
    { name: "AES-GCM", length: 256 },
    false,
    ["encrypt", "decrypt"]
  );
}

async function encryptContent(content, password) {
  const enc = new TextEncoder();
  const salt = window.crypto.getRandomValues(new Uint8Array(16));
  const iv = window.crypto.getRandomValues(new Uint8Array(12));
  const key = await deriveKey(password, salt);
  const encrypted = await window.crypto.subtle.encrypt(
    {
      name: "AES-GCM",
      iv: iv,
    },
    key,
    enc.encode(content)
  );
  return {
    encryptedContent: arrayBufferToBase64(encrypted),
    salt: arrayBufferToBase64(salt),
    iv: arrayBufferToBase64(iv),
  };
}

async function decryptContent(encryptedBase64, password, saltBase64, ivBase64) {
  const dec = new TextDecoder();
  const salt = base64ToArrayBuffer(saltBase64);
  const iv = base64ToArrayBuffer(ivBase64);
  const encrypted = base64ToArrayBuffer(encryptedBase64);
  const key = await deriveKey(password, salt);
  try {
    const decrypted = await window.crypto.subtle.decrypt(
      {
        name: "AES-GCM",
        iv: iv,
      },
      key,
      encrypted
    );
    return dec.decode(decrypted);
  } catch (e) {
    console.error("Decryption error:", e);
    return "[Decryption failed]";
  }
}

function extractPasteId(message) {
  const match = message.match(/Paste ([a-z0-9-]+) created/i);
  return match ? match[1] : "Unknown";
}

async function createPaste() {
  const content = document.getElementById("create-content").value.trim();
  const pasteId =
    document.getElementById("create-id")?.value.trim() || undefined;
  const expiryInput = document.getElementById("create-expiry");
  const expiry = expiryInput ? parseInt(expiryInput.value) || 3600 : 3600;
  const encrypt = document.getElementById("create-encrypt")?.checked || false;
  const password =
    document.getElementById("encryption-password")?.value.trim() || "";

  let payload = {
    paste_id: pasteId,
    expiry_seconds: expiry,
    content_encrypted: encrypt,
  };

  if (encrypt && password) {
    const result = await encryptContent(content, password);
    payload.content = result.encryptedContent;
    payload.salt = result.salt;
    payload.iv = result.iv;
  } else {
    payload.content = content;
  }

  fetch(`${API}/create`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
    .then((res) => res.json())
    .then((data) => {
      const id = data.paste_id || extractPasteId(data.message);
      const outputLines = [
        `✅ Paste Created Successfully!`,
        `📄 Paste ID: ${id}`,
        `⏳ Expires in: ${data.expiry_seconds} seconds`,
        `📦 Content Length: ${data.content_length} characters`,
        `🕵️ Secrets Detected: ${data.secrets_detected ? "Yes" : "No"}`,
      ];
      if (data.secrets_detected && data.secret_types.length) {
        outputLines.push(`🔒 Secret Types: ${data.secret_types.join(", ")}`);
      }
      document.getElementById("create-response").textContent =
        outputLines.join("\n");
    })
    .catch((err) => {
      document.getElementById("create-response").textContent =
        "Error: " + err.message;
    });
}

async function getPaste() {
  const idElement = document.getElementById("get-id");
  if (!idElement) {
    console.error("Input #get-id not found");
    return;
  }
  const id = idElement.value.trim();

  // Since password input removed, no password variable needed:
  // const password = ""; // or omit

  const responseBox = document.getElementById("get-response");
  if (!responseBox) {
    console.error("Response box #get-response not found");
    return;
  }

  responseBox.textContent = "Loading...";

  try {
    const res = await fetch(`${API}/paste`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ paste_id: id }),
    });

    const data = await res.json();

    if (!res.ok) {
      responseBox.textContent = `Error: ${res.status} - ${
        data.message || "Unknown error"
      }`;
      return;
    }

    // Since no encryption, just show plain content:
    if (data.content) {
      responseBox.textContent = data.content;
    } else {
      responseBox.textContent = "[❓ Unknown response structure]";
    }
  } catch (err) {
    responseBox.textContent = "Error: " + err.message;
  }
}

// Only add event listener if the checkbox exists (fixes your error)
const encryptCheckbox = document.getElementById("create-encrypt");
if (encryptCheckbox) {
  encryptCheckbox.addEventListener("change", function () {
    const wrapper = document.getElementById("password-wrapper");
    wrapper.style.display = this.checked ? "block" : "none";
  });
}

const API = "https://ohzg2ca6vj.execute-api.us-east-1.amazonaws.com";

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

  // Validate content isn't empty
  if (!content) {
    document.getElementById("create-response").textContent =
      "❌ Error: Content cannot be empty";
    return;
  }

  // Check size limit (1MB)
  const contentSize = new Blob([content]).size;
  const maxSize = 1048576;
  if (contentSize > maxSize) {
    document.getElementById(
      "create-response"
    ).textContent = `❌ Error: Content too large (${(
      contentSize / 1024
    ).toFixed(1)}KB). Maximum is 1MB.`;
    return;
  }

  const pasteId =
    document.getElementById("create-id")?.value.trim() || undefined;
  const expiryInput = document.getElementById("create-expiry");
  const expiry = expiryInput ? parseInt(expiryInput.value) || 3600 : 3600;
  const encrypt = document.getElementById("create-encrypt")?.checked || false;
  const password =
    document.getElementById("encryption-password")?.value.trim() || "";

  // Validate password if encryption enabled
  if (encrypt && !password) {
    document.getElementById("create-response").textContent =
      "❌ Error: Password required when encryption is enabled";
    return;
  }

  if (encrypt && password.length < 8) {
    document.getElementById("create-response").textContent =
      "❌ Error: Password must be at least 8 characters";
    return;
  }

  let payload = {
    paste_id: pasteId,
    expiry_seconds: expiry,
    content_encrypted: encrypt,
  };

  // Encrypt if requested
  if (encrypt && password) {
    try {
      document.getElementById("create-response").textContent =
        "🔐 Encrypting...";
      const result = await encryptContent(content, password);
      payload.content = result.encryptedContent;
      payload.salt = result.salt;
      payload.iv = result.iv;
    } catch (err) {
      document.getElementById(
        "create-response"
      ).textContent = `❌ Encryption error: ${err.message}`;
      return;
    }
  } else {
    payload.content = content;
  }

  try {
    document.getElementById("create-response").textContent = "📤 Submitting...";

    const res = await fetch(`${API}/create`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await res.json();

    if (!res.ok) {
      document.getElementById("create-response").textContent = `❌ Error ${
        res.status
      }: ${data.message || "Unknown error"}`;
      return;
    }

    const id = data.paste_id || extractPasteId(data.message);
    const outputLines = [
      `✅ Paste Created Successfully!`,
      `📄 Paste ID: ${id}`,
      `⏳ Expires in: ${data.expiry_seconds} seconds (${formatExpiry(
        data.expiry_seconds
      )})`,
      `📦 Content Length: ${data.content_length} bytes`,
    ];

    if (encrypt) {
      outputLines.push(`🔐 Encryption: Enabled (password required to view)`);
      outputLines.push(`🔑 Remember your password - it cannot be recovered!`);
    } else {
      outputLines.push(`🔓 Encryption: Disabled (plain text)`);
    }

    // Show warning if secrets detected
    if (data.secrets_detected && !encrypt) {
      outputLines.push(``);
      outputLines.push(`⚠️  WARNING: Potential secrets detected!`);
      outputLines.push(`🔒 Secret Types: ${data.secret_types.join(", ")}`);
      outputLines.push(
        `💡 Consider deleting this paste and recreating with encryption enabled.`
      );
    } else if (data.secrets_detected && encrypt) {
      outputLines.push(``);
      outputLines.push(
        `✅ Secrets detected but content is encrypted - secure!`
      );
    } else {
      outputLines.push(`✅ No sensitive patterns detected`);
    }

    document.getElementById("create-response").textContent =
      outputLines.join("\n");
  } catch (err) {
    document.getElementById(
      "create-response"
    ).textContent = `❌ Network error: ${err.message}`;
  }
}

// Helper function to format expiry time
function formatExpiry(seconds) {
  if (seconds < 3600) return `${Math.floor(seconds / 60)} minutes`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} hours`;
  return `${Math.floor(seconds / 86400)} days`;
}

// Store the fetched paste data globally so we can decrypt it without refetching
let cachedPasteData = null;

async function getPaste() {
  const idElement = document.getElementById("get-id");
  if (!idElement) {
    console.error("Input #get-id not found");
    return;
  }
  const id = idElement.value.trim();

  if (!id) {
    document.getElementById("get-response").textContent =
      "❌ Please enter a Paste ID";
    return;
  }

  const responseBox = document.getElementById("get-response");
  const passwordWrapper = document.getElementById("get-password-wrapper");
  const passwordInput = document.getElementById("get-password");

  if (!responseBox) {
    console.error("Response box #get-response not found");
    return;
  }

  // If we have cached data and user entered password, try to decrypt
  if (cachedPasteData && cachedPasteData.encrypted) {
    const password = passwordInput ? passwordInput.value.trim() : "";

    if (!password) {
      responseBox.textContent =
        "❌ Please enter the decryption password above.";
      return;
    }

    try {
      responseBox.textContent = "🔓 Decrypting...";

      const decrypted = await decryptContent(
        cachedPasteData.content,
        password,
        cachedPasteData.salt,
        cachedPasteData.iv
      );

      if (decrypted === "[Decryption failed]") {
        responseBox.textContent =
          "❌ Decryption failed. Wrong password? Try again.";
        // Keep password field visible
      } else {
        responseBox.textContent = `🔓 Decrypted content:\n\n${decrypted}\n\n⚠️ This was a one-time paste and has been destroyed.`;
        // Clear cache and hide password field
        cachedPasteData = null;
        if (passwordWrapper) passwordWrapper.style.display = "none";
        if (passwordInput) passwordInput.value = "";
        if (idElement) idElement.value = "";
      }
    } catch (err) {
      console.error("Decryption error:", err);
      responseBox.textContent = `❌ Decryption error: ${err.message}`;
    }
    return;
  }

  // Otherwise, fetch the paste from API (only happens once)
  responseBox.textContent = "🔍 Fetching paste...";

  // Hide password field initially
  if (passwordWrapper) {
    passwordWrapper.style.display = "none";
  }

  try {
    const res = await fetch(`${API}/paste`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ paste_id: id }),
    });

    const data = await res.json();

    console.log("Full API response:", data);

    if (!res.ok) {
      cachedPasteData = null; // Clear cache on error

      if (res.status === 410) {
        responseBox.textContent = `⏰ ${data.message}`;
      } else if (res.status === 404) {
        responseBox.textContent = `❌ Paste not found. Check the ID and try again.`;
      } else {
        responseBox.textContent = `❌ Error ${res.status}: ${
          data.message || "Unknown error"
        }`;
      }
      return;
    }

    // Cache the paste data
    cachedPasteData = data;

    // Check if the paste is encrypted
    if (data.encrypted === true) {
      console.log("Paste is encrypted, asking for password...");

      // Check if we have the required decryption metadata
      if (!data.salt || !data.iv) {
        responseBox.textContent =
          "❌ Error: Missing encryption metadata (salt/iv)";
        cachedPasteData = null;
        return;
      }

      // Show password field
      if (passwordWrapper) {
        passwordWrapper.style.display = "block";
      }
      responseBox.textContent =
        "🔐 This paste is encrypted.\nEnter the password above and click 'Fetch Paste' again to decrypt.";
    } else {
      // Plain text paste - show immediately
      console.log("Paste is not encrypted, showing content");
      if (data.content) {
        responseBox.textContent = `${data.content}\n\n⚠️ This was a one-time paste and has been destroyed.`;
        cachedPasteData = null; // Clear cache
        if (idElement) idElement.value = ""; // Clear ID field
      } else {
        console.log("No content field in response. Full data:", data);
        responseBox.textContent = `[❓ No content in response]\n\nDebug: ${JSON.stringify(
          data,
          null,
          2
        )}`;
        cachedPasteData = null;
      }
    }
  } catch (err) {
    console.error("Fetch error:", err);
    responseBox.textContent = "❌ Network error: " + err.message;
    cachedPasteData = null;
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

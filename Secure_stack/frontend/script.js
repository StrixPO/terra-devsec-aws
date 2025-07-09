const API = "https://ceboltsdnl.execute-api.us-east-1.amazonaws.com";

function createPaste() {
  const content = document.getElementById("create-content").value;
  const pasteId = document.getElementById("create-id").value;
  const expiry =
    parseInt(document.getElementById("create-expiry").value) || 3600;
  const encrypt = document.getElementById("create-encrypt").checked;

  const payload = {
    paste_id: pasteId || undefined,
    content: encrypt ? btoa(content) : content,
    expiry_seconds: expiry,
    content_encrypted: encrypt,
  };

  fetch(`${API}/create`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
    .then((res) => res.json())
    .then((data) => {
      document.getElementById("create-response").textContent = JSON.stringify(
        data,
        null,
        2
      );
    })
    .catch((err) => {
      document.getElementById("create-response").textContent =
        "Error: " + err.message;
    });
}
async function getPaste() {
  const id = document.getElementById("get-id").value;
  const responseBox = document.getElementById("get-response");
  responseBox.textContent = "Loading...";

  try {
    const res = await fetch(`${API}/paste/${id}`);
    const data = await res.json();

    if (!res.ok) {
      responseBox.textContent = `Error: ${res.status} - ${
        data.message || "Unknown error"
      }`;
      return;
    }

    if (data.content) {
      let content = data.content;
      if (data.encrypted) {
        try {
          content = atob(content);
        } catch (e) {
          content = "[Decryption failed]";
        }
      }
      responseBox.textContent = content;
    } else {
      responseBox.textContent = JSON.stringify(data, null, 2);
    }
  } catch (err) {
    responseBox.textContent = "Error: " + err.message;
  }
}

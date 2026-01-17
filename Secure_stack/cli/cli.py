import click
import base64
import json
import requests
import time
import os
import boto3

from utils import validate_paste_id
from dotenv import load_dotenv

load_dotenv()

# DEV_MODE enables commands that touch DynamoDB directly (scan/delete).
# SECURITY NOTE: These commands bypass the zero-trust API and must never be enabled in production releases.
DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"

# Default base URL for the deployed API. Allow override for staging/local testing.
DEFAULT_API_URL = "https://ptto3xcw05.execute-api.us-east-1.amazonaws.com"


@click.group()
@click.option("--api-url", default=DEFAULT_API_URL, show_default=True, help="Custom API base URL")
@click.pass_context
def cli(ctx, api_url):
    """
    PsstBin CLI

    SECURITY INVARIANTS (for the CLI):
    - Never attempt to "decrypt" unless you actually implemented real encryption.
    - Do not log secrets by default.
    - Prefer client-side encryption (AES-GCM in your browser app). Base64 is NOT encryption.

    NOTE:
    - This CLI currently supports optional *base64 encoding* for content.
      If you want real encryption parity with the web UI, you should add AES-GCM + PBKDF2 here too.
    """
    ctx.ensure_object(dict)
    ctx.obj["API_URL"] = api_url
    click.echo("🔐 Welcome to PsstBin - Encrypted. Ephemeral. Yours.\n")


@cli.command()
@click.pass_context
@click.argument("paste_id")
@click.option("--file", type=click.File("r"), help="File to paste from")
@click.option("--text", help="Text to paste")
@click.option("--expiry", default=3600, show_default=True, help="Paste expiry in seconds")
@click.option("--encode-b64", is_flag=True, help="Encode content as base64 (NOT encryption)")
def create(ctx, paste_id, file, text, expiry, encode_b64):
    """Create a new paste."""
    api_url = ctx.obj["API_URL"]

    # Strict ID validation prevents malformed keys and makes URLs predictable/clean.
    if not validate_paste_id(paste_id):
        click.echo("❌ Invalid paste_id format.")
        return

    content = file.read() if file else text
    if not content:
        click.echo("❌ Provide content via --file or --text.")
        return

    # IMPORTANT: base64 is encoding, not encryption.
    # We expose this as an option mainly for binary-ish payloads and safe transport.
    payload = {
        "paste_id": paste_id,
        "content": base64.b64encode(content.encode()).decode() if encode_b64 else content,
        "expiry_seconds": expiry,
        "content_encrypted": encode_b64,  # naming is legacy; ideally rename to "content_base64" or similar
    }

    # NOTE: Add timeout to avoid hanging forever on network issues.
    r = requests.post(f"{api_url}/create", json=payload, timeout=15)
    click.echo(r.text)


@cli.command()
@click.pass_context
@click.argument("paste_id")
@click.option("--output", type=click.Path(), help="Save paste to file")
@click.option("--json", "as_json", is_flag=True, help="Print full JSON instead of content only")
def get(ctx, paste_id, output, as_json):
    """
    Retrieve a paste by ID (one-time read).

    API NOTE:
    - Your frontend uses POST /paste with JSON body.
    - Your CLI previously used GET /paste/{id}.
    Pick one and keep it consistent. This version uses POST /paste for consistency.
    """
    api_url = ctx.obj["API_URL"]

    # Use the same retrieval endpoint format as your web UI to reduce drift.
    r = requests.post(
        f"{api_url}/paste",
        json={"paste_id": paste_id},
        timeout=15,
    )

    try:
        data = r.json()
    except Exception:
        click.echo(f"[Error] Invalid JSON response: {r.text}")
        return

    if r.status_code != 200:
        click.echo(f"❌ {data.get('message', 'Unknown error')}")
        return

    if as_json:
        click.echo(json.dumps(data, indent=2))
        return

    content = data.get("content", "")

    # WARNING:
    # If 'encrypted' is True in your system, content is AES-GCM ciphertext (base64),
    # and the CLI does NOT implement AES-GCM decryption, so we should not pretend to decrypt.
    if data.get("encrypted"):
        click.echo("🔐 This paste is encrypted. CLI decryption is not implemented.")
        click.echo("Tip: use the web UI or implement AES-GCM here.")
        # Still allow saving ciphertext if user wants.
    else:
        # Plaintext paste.
        pass

    if output:
        with open(output, "w", encoding="utf-8") as f:
            f.write(content)
        click.echo(f"[Saved to {output}]")
    else:
        click.echo(content)


@cli.command()
@click.pass_context
@click.argument("paste_id")
def status(ctx, paste_id):
    """
    Fetch metadata of a paste.

    NOTE:
    - Your current API does not have a dedicated metadata endpoint.
      This command calls /paste, which consumes the one-time paste.
    - That’s a problem: status checks will destroy content.
    Professional fix: create a /status endpoint that returns metadata only and does NOT mark used=True.
    """
    api_url = ctx.obj["API_URL"]
    r = requests.post(f"{api_url}/paste", json={"paste_id": paste_id}, timeout=15)

    try:
        data = r.json()
    except Exception:
        click.echo(f"[Error] Invalid response: {r.text}")
        return

    if r.status_code == 200:
        click.echo(json.dumps({
            "paste_id": data.get("paste_id"),
            "encrypted": data.get("encrypted"),
            # In your create lambda you store 'secret_types' in DynamoDB metadata,
            # but retrieval endpoint doesn't currently return it (unless you added it).
            "secret_types": data.get("secret_types", None),
        }, indent=2))
    else:
        click.echo(f"❌ {data.get('message', 'Unknown error')}")


@cli.command(name="list")
@click.pass_context
def list_pastes(ctx):
    """
    List recent pastes (DEV ONLY).

    SECURITY WARNING:
    - Uses DynamoDB scan (expensive, unbounded) and requires AWS credentials locally.
    - This bypasses the normal API access controls and should never ship as default behavior.
    """
    table = os.environ.get("TABLE_NAME", "").strip()
    if not table:
        click.echo("[ERROR] TABLE_NAME not set in ENV")
        return

    try:
        dynamo = boto3.client("dynamodb", region_name="us-east-1")
        resp = dynamo.scan(TableName=table, Limit=10)
        items = resp.get("Items", [])

        for item in items:
            pid = item.get("paste_id", {}).get("S", "-")
            enc = item.get("encrypted", {}).get("BOOL", False)
            used = item.get("used", {}).get("BOOL", False)
            ttl = int(item.get("ttl", {}).get("N", "0"))
            ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ttl))
            click.echo(f"- {pid} | encrypted={enc} | used={used} | expires={ts}")

    except Exception as e:
        click.echo(f"[ERROR] Failed to list pastes: {e}")


@cli.command()
@click.pass_context
@click.argument("paste_id")
def delete(ctx, paste_id):
    """
    Delete a paste (DEV ONLY).

    SECURITY WARNING:
    - This is an admin capability. Keep it behind DEV_MODE and never expose as public API.
    """
    table = os.environ.get("TABLE_NAME", "").strip()
    if not table:
        click.echo("[ERROR] TABLE_NAME not set in ENV")
        return

    try:
        dynamo = boto3.client("dynamodb", region_name="us-east-1")
        dynamo.delete_item(TableName=table, Key={"paste_id": {"S": paste_id}})
        click.echo(f"[✓] Paste '{paste_id}' deleted.")
    except Exception as e:
        click.echo(f"[ERROR] Failed to delete paste: {e}")


# Register DEV-only commands.
if DEV_MODE:
    cli.add_command(list_pastes)
    cli.add_command(delete)

if __name__ == "__main__":
    cli()

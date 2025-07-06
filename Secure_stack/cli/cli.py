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
DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"
DEFAULT_API_URL = "https://ptto3xcw05.execute-api.us-east-1.amazonaws.com"

@click.group()
@click.option('--api-url', default=DEFAULT_API_URL, help='Custom API base URL')
@click.pass_context
def cli(ctx, api_url):
    """SecurePaste CLI - createe and fetch secure pastes."""
    ctx.ensure_object(dict)
    ctx.obj['API_URL'] = api_url


@cli.command()
@click.pass_context
@click.argument('paste_id')
@click.option('--file', type=click.File('r'), help='File to paste from')
@click.option('--text', help='Text to paste')
@click.option('--expiry', default=3600, help='Paste expiry in seconds')
@click.option('--encrypt', is_flag=True, help='Enable base64 encryption')
def create(ctx, paste_id, file, text, expiry, encrypt):
    """Create a new secure paste."""
    api_url = ctx.obj['API_URL']

    if not validate_paste_id(paste_id):
        click.echo("Invalid paste_id format.")
        return

    content = file.read() if file else text
    if not content:
        click.echo("Please provide content via --file or --text.")
        return

    payload = {
        "paste_id": paste_id,
        "content": base64.b64encode(content.encode()).decode() if encrypt else content,
        "expiry_seconds": expiry,
        "content_encrypted": encrypt
    }

    r = requests.post(f"{api_url}/create", json=payload)
    click.echo(r.text)


@cli.command()
@click.pass_context
@click.argument('paste_id')
@click.option('--output', type=click.Path(), help='Save paste to file')
@click.option('--json', 'as_json', is_flag=True, help='Return full JSON instead of content only')
def get(ctx, paste_id, output, as_json):
    """Retrieve a paste by ID."""
    api_url = ctx.obj['API_URL']
    r = requests.get(f"{api_url}/paste/{paste_id}")

    try:
        data = r.json()
    except Exception:
        click.echo(f"[Error] Invalid response: {r.text}")
        return

    if r.status_code == 200:
        if as_json:
            click.echo(json.dumps(data, indent=2))
            return
        content = data.get("content", "")
        if data.get("encrypted"):
            try:
                content = base64.b64decode(content).decode()
                click.echo("[Decrypted]")
            except Exception:
                click.echo("[Error decoding encrypted content]")
        if output:
            with open(output, "w") as f:
                f.write(content)
            click.echo(f"[Saved to {output}]")
        else:
            click.echo(content)
    else:
        click.echo(f"[Error] {data.get('message', 'Unknown error')}")


@cli.command()
@click.pass_context
@click.argument('paste_id')
def status(ctx, paste_id):
    """Check metadata of a paste (expiry, secret types, etc.)"""
    api_url = ctx.obj['API_URL']
    r = requests.get(f"{api_url}/paste/{paste_id}")
    try:
        data = r.json()
    except Exception:
        click.echo(f"[Error] Invalid response: {r.text}")
        return

    if r.status_code == 200:
        click.echo(json.dumps({
            "paste_id": data.get("paste_id"),
            "encrypted": data.get("encrypted"),
            "has_secrets": data.get("secret_types", "") != "",
            "secret_types": data.get("secret_types", ""),
        }, indent=2))
    else:
        click.echo(f"[Error] {data.get('message', 'Unknown error')}")


@cli.command()
@click.pass_context
def list(ctx):
    """List recent pastes (dev only)"""
    table = os.environ.get("TABLE_NAME", "").strip()
    if not table:
        click.echo("[ERROR] TABLE_NAME not set in ENV")
        return

    try:
        dynamo = boto3.client("dynamodb", region_name="us-east-1")
        resp = dynamo.scan(
            TableName=table,
            Limit=10,
        )
        items = resp.get("Items", [])
        for item in items:
            pid = item.get("paste_id", {}).get("S", "-")
            enc = item.get("encrypted", {}).get("BOOL", False)
            used = item.get("used", {}).get("BOOL", False)
            ttl = int(item.get("ttl", {}).get("N", "0"))
            ts = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ttl))
            click.echo(f"- {pid} | encrypted={enc} | used={used} | expires={ts}")
    except Exception as e:
        click.echo(f"[ERROR] Failed to list pastes: {e}")


@cli.command()
@click.pass_context
@click.argument("paste_id")
def delete(ctx, paste_id):
    """DELETE a paste (dev)"""
    table = os.environ.get("TABLE_NAME", "").strip()
    try:
        dynamo = boto3.client("dynamodb", region_name="us-east-1")
        dynamo.delete_item(
            TableName=table,
            Key={"paste_id": {"S": paste_id}}
        )
        click.echo(f"[✓] Paste '{paste_id}' deleted.")
    except Exception as e:
        click.echo(f"[ERROR] Failed to delete paste: {e}")


# Register commands conditionally
if DEV_MODE:
    cli.add_command(list)
    cli.add_command(delete)

if __name__ == "__main__":
    cli()

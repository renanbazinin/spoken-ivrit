"""Shared bits: paths, the ElevenLabs key and a tiny API client (standard library only)."""
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request
import uuid

HERE = pathlib.Path(__file__).resolve().parent.parent
API = "https://api.elevenlabs.io"
ZONES = ["elwynn", "dunmorogh", "teldrassil", "durotar", "mulgore", "tirisfal"]


def api_key():
    if os.environ.get("ELEVENLABS_API_KEY"):
        return os.environ["ELEVENLABS_API_KEY"].strip()
    for env in (HERE / ".env", HERE.parent / "hebrew-samples" / ".env"):
        if env.exists():
            for row in env.read_text(encoding="utf-8-sig").splitlines():
                name, _, value = row.partition("=")
                if name.strip() == "ELEVENLABS_API_KEY" and value.strip():
                    return value.strip().strip('"').strip("'")
    sys.exit("No key: put ELEVENLABS_API_KEY=... in hebrew-pack/.env (or hebrew-samples/.env).")


def call(key, method, path, body=None, content_type="application/json", timeout=300):
    data = body if isinstance(body, bytes) or body is None else json.dumps(body).encode()
    req = urllib.request.Request(API + path, data=data, method=method, headers={"xi-api-key": key})
    if data is not None:
        req.add_header("Content-Type", content_type)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {path} -> HTTP {e.code}: {e.read().decode(errors='replace')[:600]}") from None


def multipart(fields, files):
    boundary = uuid.uuid4().hex
    out = b""
    for name, value in fields.items():
        out += f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
    for name, path in files:
        out += (
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; filename="{path.name}"\r\n'
            f"Content-Type: audio/mpeg\r\n\r\n"
        ).encode() + path.read_bytes() + b"\r\n"
    return out + f"--{boundary}--\r\n".encode(), f"multipart/form-data; boundary={boundary}"


def pack_files(clip):
    """The file names a clip ships under. This pack has one version for every player, so a
    line that English splits by the player's sex keeps its male text under the plain name
    (the addon falls back to it for any character) and the female variant is not used."""
    out = []
    for rel in clip["files"]:
        folder, _, name = rel.rpartition("/")
        if name.startswith("f-"):
            continue
        if name.startswith("m-"):
            name = name[2:]
        rel = f"{folder}/{name}"
        if rel not in out:
            out.append(rel)
    return out


def load_json(path, default=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def units():
    """Every unit of work (lines/<unit>.en.json) in working order, from lines/index.json."""
    index = load_json(HERE / "lines" / "index.json")
    return [u["unit"] for u in index["units"]] if index else list(ZONES)


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

"""Publish only the reviewed demo assets to GREG's existing public repository.

Uses Git's configured credential helper in memory; credentials are never printed.
Run only after committing and pushing the intended main revision.
"""
from pathlib import Path
import json
import subprocess

import httpx

ROOT = Path(__file__).resolve().parents[1]
REPO = "OptimistOtaku/greg"
TAG = "v0.1.0-demo"
ASSETS = {
    "greg-demo-1080p.mp4": "video/mp4",
    "greg-demo.srt": "application/x-subrip",
    "youtube-thumbnail.png": "image/png",
}


def main():
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    remote_sha = subprocess.check_output(
        ["git", "ls-remote", "origin", "refs/heads/main"], cwd=ROOT, text=True
    ).split()[0]
    if sha != remote_sha:
        raise SystemExit("Push the reviewed revision to main first.")
    credential = subprocess.run(
        ["git", "credential", "fill"], input="protocol=https\nhost=github.com\n\n",
        text=True, capture_output=True, check=True, cwd=ROOT,
    )
    fields = dict(line.split("=", 1) for line in credential.stdout.splitlines() if "=" in line)
    token = fields.get("password")
    if not token:
        raise SystemExit("GitHub credential helper did not provide a credential.")
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28"}
    with httpx.Client(headers=headers, timeout=180) as client:
        base = f"https://api.github.com/repos/{REPO}"
        repo = client.get(base)
        repo.raise_for_status()
        if repo.json().get("private") or repo.json().get("full_name") != REPO:
            raise SystemExit("Expected the existing public GREG repository; no visibility changes made.")
        response = client.get(f"{base}/releases/tags/{TAG}")
        if response.status_code == 404:
            response = client.post(f"{base}/releases", json={
                "tag_name": TAG, "target_commitish": sha,
                "name": "GREG — Graph Hacks Track 01 demo",
                "body": "90-second 1080p demo with the receipt-driven FalkorDB knowledge graph, "
                        "shared evidence and BOLT-to-ECHO body handoff.\n\n"
                        "Recorded Gemini mission; directed 3D replay with time compression. "
                        "Synthetic station and voice; original procedural score. "
                        "Thumbnail is AI-generated promotional art.\n\n"
                        "Setup, graph model, executed Cypher, evidence and limitations: see README.md. "
                        "Track 01: Agents That Act on Connected Data.",
                "draft": False, "prerelease": False,
            })
        response.raise_for_status()
        release = response.json()
        uploaded = {asset["name"]: asset for asset in release.get("assets", [])}
        urls = {}
        for name, content_type in ASSETS.items():
            path = ROOT / "artifacts" / "video" / name
            if name in uploaded:
                if uploaded[name]["size"] != path.stat().st_size:
                    raise SystemExit(f"Existing asset differs: {name}; no overwrite performed.")
                urls[name] = uploaded[name]["browser_download_url"]
                continue
            upload_url = release["upload_url"].split("{")[0]
            with path.open("rb") as stream:
                result = client.post(upload_url, params={"name": name}, content=stream,
                                     headers={"Content-Type": content_type,
                                              "Content-Length": str(path.stat().st_size)})
            result.raise_for_status()
            urls[name] = result.json()["browser_download_url"]
            print(f"Uploaded {name} ({path.stat().st_size} bytes)", flush=True)
        report = {"release_url": release["html_url"], "source_commit": sha, "assets": urls}
        (ROOT / "artifacts/video/public-release.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

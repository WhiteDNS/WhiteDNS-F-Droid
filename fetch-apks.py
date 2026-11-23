import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


APPS = (
    ("WhiteAestherMobile", "com.whitedns.whiteaesther",
     "c67cf2422c3833375bb194bb452ebd5af4d2d2dac04d84b79c300295b84c6ebf"),
    ("WhiteVPN", "com.whitedns.vpn",
     "9a6d44c8b8d2a8b6ed56bdfc7259b41e817520428cb823a12857b445ad8d27b6"),
    ("WhiteDNS-Android", "shop.whitedns.client",
     "60b38f8049880e422f99733978c5cbad2134dfbf0029684e3bf5828084527628"),
)


def fetch_apk(app, package, expected_signer, destination):
    source = f"WhiteDNS/{app}"
    release = json.loads(subprocess.check_output(
        ["gh", "api", f"repos/{source}/releases/latest"],
    ))
    if release["draft"] or release["prerelease"]:
        raise SystemExit(f"{source}: expected a stable, published release")

    assets = [
        asset for asset in release["assets"]
        if re.fullmatch(r"[A-Za-z0-9._-]+-universal\.apk", asset["name"])
    ]
    if len(assets) != 1 or not re.fullmatch(r"sha256:[0-9a-f]{64}", assets[0].get("digest") or ""):
        raise SystemExit(f"{source}: expected exactly one universal APK with a SHA-256 digest")

    asset = assets[0]
    apk = destination / f"{package}.apk"
    tag = release["tag_name"]
    subprocess.run(
        ["gh", "release", "download", "--repo", source, "--pattern", asset["name"],
         "--output", str(apk), "--", tag],
        check=True,
    )
    with apk.open("rb") as file:
        digest = hashlib.file_digest(file, "sha256").hexdigest()
    if f"sha256:{digest}" != asset["digest"]:
        raise SystemExit(f"{source}: APK digest mismatch")

    badging = subprocess.check_output(["aapt", "dump", "badging", str(apk)])
    if not badging.startswith(f"package: name='{package}' ".encode()):
        raise SystemExit(f"{source}: unexpected application ID")

    signature = subprocess.check_output(["apksigner", "verify", "--print-certs", str(apk)])
    signers = re.findall(rb"^Signer #\d+ certificate SHA-256 digest: ([a-f0-9]{64})\r?$",
                         signature, re.MULTILINE)
    if signers != [expected_signer.encode()]:
        raise SystemExit(f"{source}: unexpected APK signing certificate")
    print(f"Verified {source} {tag}: {apk.name}", flush=True)


if __name__ == "__main__":
    destination = Path(sys.argv[1])
    destination.mkdir(parents=True, exist_ok=True)
    for app in APPS:
        fetch_apk(*app, destination)

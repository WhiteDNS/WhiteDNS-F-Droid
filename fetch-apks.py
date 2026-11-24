import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


ABI_CODES = {"armeabi-v7a": 1, "arm64-v8a": 2, "x86": 3, "x86_64": 4}
APPS = (
    ("WhiteAestherMobile", "com.whitedns.whiteaesther",
     "c67cf2422c3833375bb194bb452ebd5af4d2d2dac04d84b79c300295b84c6ebf",
     "v1.18.2", 100048, ("armeabi-v7a", "arm64-v8a", "x86_64")),
    ("WhiteVPN", "com.whitedns.vpn",
     "9a6d44c8b8d2a8b6ed56bdfc7259b41e817520428cb823a12857b445ad8d27b6",
     "v1.8.1", 91, tuple(ABI_CODES)),
    ("WhiteDNS-Android", "shop.whitedns.client",
     "60b38f8049880e422f99733978c5cbad2134dfbf0029684e3bf5828084527628",
     "1.6.16", 40, tuple(ABI_CODES)),
)


def download_apk(source, tag, asset, apk, package, expected_signer, expected_abis):
    subprocess.run(
        ["gh", "release", "download", "--repo", source, "--pattern", asset["name"],
         "--output", str(apk), "--", tag],
        check=True,
    )
    with apk.open("rb") as file:
        digest = hashlib.file_digest(file, "sha256").hexdigest()
    if f"sha256:{digest}" != asset["digest"]:
        raise SystemExit(f"{source}: APK digest mismatch")

    badging = subprocess.check_output(["aapt", "dump", "badging", str(apk)]).decode()
    identity = re.match(r"package: name='([^']+)' versionCode='([0-9]+)' versionName='([^']+)'", badging)
    if not identity or identity[1] != package or identity[3] != tag.removeprefix("v"):
        raise SystemExit(f"{source}: unexpected APK package or version in {apk.name}")
    native_code = re.search(r"^native-code:(.*)$", badging, re.MULTILINE)
    if not native_code or set(re.findall(r"'([^']+)'", native_code[1])) != set(expected_abis):
        raise SystemExit(f"{source}: unexpected APK architectures in {apk.name}")

    signature = subprocess.check_output(["apksigner", "verify", "--print-certs", str(apk)])
    signers = re.findall(rb"^Signer #\d+ certificate SHA-256 digest: ([a-f0-9]{64})\r?$",
                         signature, re.MULTILINE)
    if signers != [expected_signer.encode()]:
        raise SystemExit(f"{source}: unexpected APK signing certificate")
    version_code = int(identity[2])
    print(f"Verified {source} {tag}: {apk.name} ({version_code})", flush=True)
    return version_code


def fetch_apks(app, package, expected_signer, legacy_tag, legacy_code, abis, destination):
    source = f"WhiteDNS/{app}"
    release = json.loads(subprocess.check_output(
        ["gh", "api", f"repos/{source}/releases/latest"],
    ))
    if release["draft"] or release["prerelease"]:
        raise SystemExit(f"{source}: expected a stable, published release")

    tag = release["tag_name"]
    legacy = tag == legacy_tag
    codes = {}
    for abi in ("universal",) if legacy else abis:
        assets = [
            asset for asset in release["assets"]
            if re.fullmatch(rf"[A-Za-z0-9._-]+-{re.escape(abi)}\.apk", asset["name"])
        ]
        if len(assets) != 1 or not re.fullmatch(r"sha256:[0-9a-f]{64}", assets[0].get("digest") or ""):
            raise SystemExit(f"{source}: expected exactly one {abi} APK with a SHA-256 digest")
        apk = destination / f"{package}-{abi}.apk"
        codes[abi] = download_apk(source, tag, assets[0], apk, package, expected_signer,
                                  abis if legacy else (abi,))

    if legacy:
        if codes["universal"] != legacy_code:
            raise SystemExit(f"{source}: unexpected legacy APK version code")
        return

    base_codes = {code - ABI_CODES[abi] for abi, code in codes.items()}
    if min(codes.values()) <= legacy_code or len(base_codes) != 1 or min(base_codes) % 10 != 0:
        raise SystemExit(f"{source}: incompatible APK version codes {codes}")


if __name__ == "__main__":
    destination = Path(sys.argv[1])
    destination.mkdir(parents=True, exist_ok=True)
    for app in APPS:
        fetch_apks(*app, destination)

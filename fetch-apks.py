import hashlib
import json
import re
import subprocess
import sys
from itertools import zip_longest
from pathlib import Path
from tempfile import TemporaryDirectory


ABI_CODES = {"armeabi-v7a": 1, "arm64-v8a": 2, "x86": 3, "x86_64": 4}
# GitHub Pages limits the whole site to 1 GB. Reserve space for index files and icons.
APK_BUDGET = 998_500_000
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


def github_releases(app, endpoint):
    return json.loads(subprocess.check_output(
        ["gh", "api", f"repos/WhiteDNS/{app}/releases{endpoint}"],
    ))


def version(tag):
    if re.fullmatch(r"v?\d+\.\d+\.\d+", tag):
        return tuple(map(int, tag.removeprefix("v").split(".")))
    return ()


def release_assets(source, release, legacy_tag, abis):
    if release["draft"] or release["prerelease"]:
        raise SystemExit(f"{source}: expected a stable, published release")

    tag = release["tag_name"]
    number = version(tag)
    legacy = tag == legacy_tag or (number and number < version(legacy_tag))
    selected = {}
    for abi in ("universal",) if legacy else abis:
        assets = [
            asset for asset in release["assets"]
            if re.fullmatch(rf"[A-Za-z0-9._-]+-{re.escape(abi)}\.apk", asset["name"])
        ]
        if len(assets) != 1 or not re.fullmatch(r"sha256:[0-9a-f]{64}", assets[0].get("digest") or ""):
            raise SystemExit(f"{source}: expected exactly one {abi} APK with a SHA-256 digest")
        selected[abi] = assets[0]
    return selected


def fetch_apks(app, package, expected_signer, legacy_tag, legacy_code, abis,
               destination, release, assets, newer_code=None):
    source = f"WhiteDNS/{app}"
    tag = release["tag_name"]
    with TemporaryDirectory(dir=destination.parent) as scratch:
        files = {}
        codes = {}
        for abi, asset in assets.items():
            files[abi] = Path(scratch) / f"{abi}.apk"
            codes[abi] = download_apk(source, tag, asset, files[abi], package, expected_signer,
                                      abis if abi == "universal" else (abi,))

        if "universal" in codes:
            code = codes["universal"]
            if code > legacy_code or tag == legacy_tag and code != legacy_code:
                raise SystemExit(f"{source}: unexpected legacy APK version code")
        else:
            base_codes = {code - ABI_CODES[abi] for abi, code in codes.items()}
            if min(codes.values()) <= legacy_code or len(base_codes) != 1 or min(base_codes) % 10 != 0:
                raise SystemExit(f"{source}: incompatible APK version codes {codes}")

        if newer_code is not None and max(codes.values()) >= newer_code:
            raise SystemExit(f"{source}: historical APKs must rank below newer releases")
        for abi, file in files.items():
            file.rename(destination / f"{package}_{codes[abi]}.apk")
    return min(codes.values())


def recent_history(app, latest_tag):
    latest = version(latest_tag)
    seen = set()
    recent = []
    for release in sorted(github_releases(app, "?per_page=30"),
                          key=lambda item: version(item["tag_name"]), reverse=True):
        number = version(release["tag_name"])
        if number and number < latest and number not in seen and not (release["draft"] or release["prerelease"]):
            seen.add(number)
            recent.append(release)
            if len(recent) == 2:
                break
    return recent


def publish_apks(destination):
    remaining = APK_BUDGET
    newest_codes = {}
    releases = [github_releases(app[0], "/latest") for app in APPS]
    history = zip_longest(*(recent_history(app[0], release["tag_name"])
                            for app, release in zip(APPS, releases)))
    for batch in (releases, *history):
        for app, release in zip(APPS, batch):
            if release is None:
                continue
            source, package, _, legacy_tag, _, abis = app
            newer_code = newest_codes.get(package)
            try:
                assets = release_assets(source, release, legacy_tag, abis)
                size = sum(asset["size"] for asset in assets.values())
                if size > remaining:
                    raise SystemExit("APK budget for GitHub Pages exceeded")
                newest_codes[package] = fetch_apks(*app, destination, release, assets, newer_code)
            except (SystemExit, subprocess.CalledProcessError) as error:
                if newer_code is None:
                    raise
                print(f"Skipped history for {source} {release['tag_name']}: {error}", flush=True)
                continue
            remaining -= size


if __name__ == "__main__":
    destination = Path(sys.argv[1])
    destination.mkdir(parents=True, exist_ok=True)
    publish_apks(destination)

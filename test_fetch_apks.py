import importlib.util
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


spec = importlib.util.spec_from_file_location("fetch_apks", Path(__file__).with_name("fetch-apks.py"))
fetcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fetcher)


class ReleaseSelectionTest(unittest.TestCase):
    app = fetcher.APPS[1]

    def release(self, tag, outputs, codes, newer_code=None):
        release = {
            "draft": False,
            "prerelease": False,
            "tag_name": tag,
            "assets": [{"name": f"WhiteVPN-{tag}-{abi}.apk", "digest": "sha256:" + "a" * 64}
                       for abi in outputs],
        }
        assets = fetcher.release_assets(self.app[0], release, self.app[3], self.app[5])
        observed = iter(codes)

        def mock_download(source, tag, asset, apk, package, signer, abis):
            apk.touch()
            return next(observed)

        with TemporaryDirectory() as work, patch.object(fetcher, "download_apk", side_effect=mock_download) as download:
            fetcher.fetch_apks(*self.app, Path(work), release, assets, newer_code)
            return [call.args[-1] for call in download.call_args_list]

    def test_legacy_release_publishes_only_universal(self):
        abis = tuple(fetcher.ABI_CODES)
        self.assertEqual(self.release("v1.8.1", (*abis, "universal"), [91]), [abis])

    def test_new_release_publishes_each_architecture_once(self):
        abis = tuple(fetcher.ABI_CODES)
        self.assertEqual(self.release("v1.8.2", (*abis, "universal"), [921, 922, 923, 924]),
                         [(abi,) for abi in abis])

    def test_new_release_rejects_incomplete_or_equal_codes(self):
        abis = tuple(fetcher.ABI_CODES)
        with self.assertRaisesRegex(SystemExit, "exactly one arm64-v8a"):
            self.release("v1.8.2", ("armeabi-v7a", "universal"), [921])
        with self.assertRaisesRegex(SystemExit, "incompatible APK version codes"):
            self.release("v1.8.2", abis, [920, 920, 920, 920])

    def test_history_supports_legacy_universal_with_lower_code(self):
        abis = tuple(fetcher.ABI_CODES)
        self.assertEqual(self.release("v1.7.1", (*abis, "universal"), [84], 91), [abis])
        with self.assertRaisesRegex(SystemExit, "historical APKs must rank below"):
            self.release("v1.7.1", ("universal",), [91], 91)

    def test_history_excludes_prereleases_and_keeps_two_stable_versions(self):
        releases = [{"tag_name": tag, "draft": False, "prerelease": early} for tag, early in (
            ("v1.7.1", False), ("v1.8.2", False), ("v1.9.0", False),
            ("v1.8.1", True), ("v1.8.0", False), ("v1.7.0", False),
        )]
        with patch.object(fetcher, "github_releases", return_value=releases):
            self.assertEqual([item["tag_name"] for item in fetcher.recent_history("WhiteVPN", "v1.8.2")],
                             ["v1.8.0", "v1.7.1"])

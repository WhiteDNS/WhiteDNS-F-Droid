import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import patch


spec = importlib.util.spec_from_file_location("fetch_apks", Path(__file__).with_name("fetch-apks.py"))
fetcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fetcher)


class ReleaseSelectionTest(unittest.TestCase):
    app = fetcher.APPS[1]

    def release(self, tag, outputs, codes):
        payload = json.dumps({
            "draft": False,
            "prerelease": False,
            "tag_name": tag,
            "assets": [{"name": f"WhiteVPN-{tag}-{abi}.apk", "digest": "sha256:" + "a" * 64}
                       for abi in outputs],
        }).encode()
        with patch.object(fetcher.subprocess, "check_output", return_value=payload):
            with patch.object(fetcher, "download_apk", side_effect=codes) as download:
                fetcher.fetch_apks(*self.app, Path("repo"))
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

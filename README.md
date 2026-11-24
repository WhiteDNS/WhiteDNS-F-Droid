# WhiteDNS F-Droid repository

<p>
  <a href="https://whitedns.github.io/WhiteDNS-F-Droid/">
    <img src="https://f-droid.org/assets/fdroid-logo.svg" alt="" width="40" align="middle">
    <strong>Add the WhiteDNS repository to F-Droid</strong>
  </a>
</p>

Install and update WhiteAesther, WhiteVPN and WhiteDNS Android from a single repository in F-Droid. Open the setup page on your Android device and tap the button to add the repository.

The workflow checks GitHub Releases every six hours and can also run manually. It verifies each stable APK's digest, package ID, release certificate, architecture and version code before publishing on GitHub Pages. F-Droid selects a smaller APK compatible with the device. An app remains on its last universal release until it publishes architecture-specific APKs with distinct version codes.

A separate monthly job records a maintenance commit so GitHub keeps running the schedule when this repository is otherwise idle.

For setup, set the Pages source to GitHub Actions. Create and back up a PKCS#12 repository key with alias `whitedns-fdroid`. Store the base64-encoded keystore in `FDROID_KEYSTORE_BASE64` and its password in `FDROID_KEYSTORE_PASSWORD` in Actions secrets. The repository key signs the index. App signing keys are managed by the individual app projects.

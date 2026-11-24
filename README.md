# WhiteDNS F-Droid repository

<p>
  <a href="https://whitedns.github.io/WhiteDNS-F-Droid/">
    <img src="https://f-droid.org/assets/fdroid-logo.svg" alt="" width="40" align="middle">
    <strong>Add the WhiteDNS repository to F-Droid</strong>
  </a>
</p>

Install and update WhiteAesther, WhiteVPN and WhiteDNS Android from a single repository in F-Droid. Open the setup page on your Android device and tap the button to add the repository.

The workflow checks GitHub Releases every six hours and can also run manually. It verifies each stable APK's digest, package ID, release certificate, architecture and version code before publishing on GitHub Pages. F-Droid selects a smaller APK compatible with the device. The index includes up to three stable releases per app within the Pages size limit. The current releases take priority, followed by the most recent historical release for each app. Older releases from before the ABI version-code migration use their verified universal APK.

The app listings are maintained in `metadata/`. The website and Telegram links there are shared across all three apps.

A separate monthly job records a maintenance commit so GitHub keeps running the schedule when this repository is otherwise idle.

For setup, set the Pages source to GitHub Actions. Create and back up a PKCS#12 repository key with alias `whitedns-fdroid`. Store the base64-encoded keystore in `FDROID_KEYSTORE_BASE64` and its password in `FDROID_KEYSTORE_PASSWORD` in Actions secrets. The repository key signs the index. App signing keys are managed by the individual app projects.

## Cloudflare R2 mirror

Connect a dedicated R2 bucket to a public custom domain. Create an R2 Object Read & Write token scoped to that bucket. Keep the public domain free of sign-in and browser challenges so F-Droid can fetch files directly.

Set the repository Actions variables `FDROID_R2_BUCKET` to the bucket name, `FDROID_R2_ENDPOINT` to its S3 HTTPS endpoint and `FDROID_MIRROR_ORIGIN` to the custom domain's HTTPS origin without a path. Set `FDROID_R2_ACCESS_KEY_ID` and `FDROID_R2_SECRET_ACCESS_KEY` in Actions secrets before setting the origin variable.

The existing Workflow uploads and verifies the same signed index on R2 before publishing it on Pages. Share `/index.html` on the custom domain to add the mirror with the existing repository fingerprint. The R2 bucket retains older APK objects while clients may still have a cached index.

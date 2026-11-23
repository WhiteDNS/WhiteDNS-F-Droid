# WhiteDNS F-Droid repository

Install and update WhiteAesther, WhiteVPN and WhiteDNS Android from a single repository in F-Droid. Open the setup page on your Android device and tap the button to add the repository. [Add WhiteDNS to F-Droid](https://whitedns.github.io/WhiteDNS-F-Droid/)

The workflow checks GitHub Releases every six hours and can also run manually. It downloads the latest stable universal APK for each app, checks the GitHub asset digest and the app's package ID and release certificate, then publishes all three together on GitHub Pages. Each APK keeps its original signature.

For setup, set the Pages source to GitHub Actions. Create and back up a PKCS#12 repository key with alias `whitedns-fdroid`. Store the base64-encoded keystore in `FDROID_KEYSTORE_BASE64` and its password in `FDROID_KEYSTORE_PASSWORD` in Actions secrets. The repository key signs the index. App signing keys are managed by the individual app projects.

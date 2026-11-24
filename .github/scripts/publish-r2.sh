#!/usr/bin/env bash
set -euo pipefail

: "${AWS_ACCESS_KEY_ID:?Set FDROID_R2_ACCESS_KEY_ID}"
: "${AWS_SECRET_ACCESS_KEY:?Set FDROID_R2_SECRET_ACCESS_KEY}"
[[ "$FDROID_R2_BUCKET" =~ ^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$ ]]
[[ "$FDROID_R2_ENDPOINT" =~ ^https://[a-f0-9]{32}(\.(eu|us|fedramp))?\.r2\.cloudflarestorage\.com$ ]]

s3=(aws --endpoint-url "$FDROID_R2_ENDPOINT" s3)
bucket="s3://$FDROID_R2_BUCKET"
site=build/site
repo=fdroid/repo
indexes=(index.xml index.jar index-v1.jar index-v2.json entry.jar)

exclude=(--exclude index.html)
for file in "${indexes[@]}"; do
    exclude+=(--exclude "$repo/$file")
done
"${s3[@]}" sync "$site/" "$bucket/" "${exclude[@]}" --only-show-errors
"${s3[@]}" cp build/mirror-index.html "$bucket/index.html" --cache-control no-store --only-show-errors

# Keep APKs from earlier indexes available for clients with a cached index.
for file in "${indexes[@]}"; do
    if [[ -f "$site/$repo/$file" ]]; then
        "${s3[@]}" cp "$site/$repo/$file" "$bucket/$repo/$file" --cache-control no-store --only-show-errors
    fi
done

download=$(mktemp)
trap 'rm -f "$download"' EXIT
for file in entry.jar index-v2.json; do
    curl --fail --silent --show-error --retry 3 --retry-all-errors --max-time 20 \
        "$FDROID_MIRROR_ORIGIN/$repo/$file" --output "$download"
    cmp "$download" "$site/$repo/$file"
done
printf 'R2 mirror: %s/index.html\n' "$FDROID_MIRROR_ORIGIN" >> "$GITHUB_STEP_SUMMARY"

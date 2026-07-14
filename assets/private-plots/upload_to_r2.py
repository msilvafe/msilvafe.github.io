#!/usr/bin/env python3
"""Upload a directory of images to the msilvafe-plots R2 bucket, preserving
the relative path structure under assets/private-plots/ as the object key.

Credentials are read from environment variables (never hardcoded, never
written to disk by this script): R2_ACCOUNT_ID, R2_ACCESS_KEY_ID,
R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME.

Usage:
    R2_ACCOUNT_ID=... R2_ACCESS_KEY_ID=... R2_SECRET_ACCESS_KEY=... R2_BUCKET_NAME=... \
        python3 upload_to_r2.py <local_dir> <key_prefix>
"""
import os
import sys
import mimetypes
from pathlib import Path

import boto3
from botocore.config import Config

def main():
    if len(sys.argv) != 3:
        print("Usage: upload_to_r2.py <local_dir> <key_prefix>")
        sys.exit(1)

    local_dir = Path(sys.argv[1])
    key_prefix = sys.argv[2].strip("/")

    account_id = os.environ["R2_ACCOUNT_ID"]
    access_key = os.environ["R2_ACCESS_KEY_ID"]
    secret_key = os.environ["R2_SECRET_ACCESS_KEY"]
    bucket = os.environ["R2_BUCKET_NAME"]

    s3 = boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )

    files = sorted(p for p in local_dir.rglob("*") if p.is_file())
    for f in files:
        rel = f.relative_to(local_dir).as_posix()
        key = f"{key_prefix}/{rel}"
        content_type = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
        # HTML (gallery index/hub pages) gets a short cache lifetime since it's
        # re-published in place under the same URL every time a gallery is
        # updated -- a long cache here means visitors (and Cloudflare's edge)
        # keep serving a stale listing. Images get a much shorter cache too
        # (not the previous 1-year default) since filenames can be reused
        # across re-publishes of the same topic dir.
        if content_type == "text/html":
            cache_control = "public, max-age=60, must-revalidate"
        else:
            cache_control = "public, max-age=3600"
        s3.upload_file(
            str(f), bucket, key,
            ExtraArgs={"ContentType": content_type, "CacheControl": cache_control},
        )
        print(f"uploaded: {key} ({content_type}, cache={cache_control})")

    print(f"\nDone. {len(files)} file(s) uploaded to bucket '{bucket}' under prefix '{key_prefix}/'.")

if __name__ == "__main__":
    main()

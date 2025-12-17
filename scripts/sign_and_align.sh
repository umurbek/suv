#!/usr/bin/env bash
# Sign and align an unsigned Cordova release APK using apksigner and zipalign.
# Edit KEYSTORE, ALIAS and BUILD_TOOLS_VERSION before running.

set -euo pipefail

UNSIGNED_APK="platforms/android/app/build/outputs/apk/release/app-release-unsigned.apk"
KEYSTORE_PATH="${HOME}/my-release-key.jks"   # change to your keystore
KEYSTORE_ALIAS="my_alias"                    # change to your alias
OUT_SIGNED="app-release-signed.apk"
OUT_ALIGNED="app-release-aligned.apk"
BUILD_TOOLS_VERSION="33.0.2"                 # change to your installed build-tools

if [ ! -f "$UNSIGNED_APK" ]; then
  echo "Unsigned APK not found: $UNSIGNED_APK"
  exit 2
fi

APKSIGNER="$ANDROID_SDK_ROOT/build-tools/$BUILD_TOOLS_VERSION/apksigner"
ZIPALIGN="$ANDROID_SDK_ROOT/build-tools/$BUILD_TOOLS_VERSION/zipalign"

if [ ! -x "$APKSIGNER" ]; then
  echo "apksigner not found at $APKSIGNER"
  exit 3
fi
if [ ! -x "$ZIPALIGN" ]; then
  echo "zipalign not found at $ZIPALIGN"
  exit 4
fi

# Sign
echo "Signing APK..."
$APKSIGNER sign --ks "$KEYSTORE_PATH" --out "$OUT_SIGNED" "$UNSIGNED_APK"

# Align
echo "Aligning APK..."
$ZIPALIGN -v -p 4 "$OUT_SIGNED" "$OUT_ALIGNED"

echo "Signed+aligned APK: $OUT_ALIGNED"

exit 0

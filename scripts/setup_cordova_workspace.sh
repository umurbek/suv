#!/usr/bin/env bash
# setup_cordova_workspace.sh
# Creates a Cordova project in the repository at ./cordova_app,
# copies prepared template `cordova_template/www` into it and adds Android platform.
# Run this locally (requires cordova, Java JDK, Android SDK installed).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CORDOVA_DIR="$REPO_ROOT/cordova_app"
TEMPLATE_WWW="$REPO_ROOT/cordova_template/www"
APP_ID="com.example.myapp"
APP_NAME="MyApp"

echo "Repo root: $REPO_ROOT"

if [ -d "$CORDOVA_DIR" ]; then
  echo "Cordova project already exists at $CORDOVA_DIR"
else
  echo "Creating Cordova project at $CORDOVA_DIR"
  cordova create "$CORDOVA_DIR" "$APP_ID" "$APP_NAME"
fi

# backup existing www in cordova project if any
if [ -d "$CORDOVA_DIR/www" ]; then
  echo "Backing up existing $CORDOVA_DIR/www -> $CORDOVA_DIR/www.bak"
  rm -rf "$CORDOVA_DIR/www.bak" || true
  mv "$CORDOVA_DIR/www" "$CORDOVA_DIR/www.bak" || true
fi

# Copy template www
if [ -d "$TEMPLATE_WWW" ]; then
  echo "Copying template www -> $CORDOVA_DIR/www"
  cp -r "$TEMPLATE_WWW" "$CORDOVA_DIR/www"
else
  echo "Template www not found at $TEMPLATE_WWW" >&2
  exit 2
fi

cd "$CORDOVA_DIR"

# Add android platform if missing
if ! cordova platforms ls | grep -q "android"; then
  echo "Adding Android platform"
  cordova platform add android
else
  echo "Android platform already added"
fi

echo "Setup complete. Next steps (run locally):"
echo "  cd $CORDOVA_DIR"
echo "  # edit www/js/config.js to set API_BASE to your server domain"
echo "  cordova build android   # builds debug APK"
echo "  adb install -r platforms/android/app/build/outputs/apk/debug/app-debug.apk"

echo "If you want to build release and sign, use scripts/sign_and_align.sh after building release."

exit 0

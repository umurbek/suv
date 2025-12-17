#!/usr/bin/env bash
# Helper script to create a Cordova project and build debug APK
# Edit variables below before running.

set -euo pipefail

CORDOVA_PROJECT_DIR="$HOME/cordova_myapp"  # change as needed
APP_ID="com.example.myapp"
APP_NAME="MyApp"

echo "=== Cordova create + build helper ==="

echo "1) Ensure Node.js, npm, Java JDK and Android SDK are installed."

echo "2) Create project (if not exists)"
if [ ! -d "$CORDOVA_PROJECT_DIR" ]; then
  cordova create "$CORDOVA_PROJECT_DIR" "$APP_ID" "$APP_NAME"
fi

cd "$CORDOVA_PROJECT_DIR"

# Add Android platform if missing
if ! cordova platforms ls | grep -q "android"; then
  cordova platform add android
fi

# Copy your web assets into www/ (do this manually or via build step)
# For example: cp -r /path/to/your/www/* $CORDOVA_PROJECT_DIR/www/

# Build debug APK
cordova build android

echo "Debug APK built at: $CORDOVA_PROJECT_DIR/platforms/android/app/build/outputs/apk/debug/app-debug.apk"

echo "To install on attached device: adb install -r $CORDOVA_PROJECT_DIR/platforms/android/app/build/outputs/apk/debug/app-debug.apk"

exit 0

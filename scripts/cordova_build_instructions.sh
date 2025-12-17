#!/bin/bash
# Cordova Android build helper (instructions + commands)
# Usage: read the file and run specific commands manually.

set -e
echo "This file contains reference commands for building a Cordova Android app.\nEdit variables below before running any command."

# --- Edit these ---
CORDOVA_PROJECT_DIR="/path/to/your/cordova/project"  # change this
ANDROID_SDK_BUILD_TOOLS_VERSION="33.0.2"              # adjust to installed build-tools
KEYSTORE_PATH="$HOME/my-release-key.jks"              # path to your keystore (create with keytool)
KEY_ALIAS="my_alias"

# Examples of helpful commands (do not run blindly; check values above):

echo "\n1) Install Cordova (if not installed):"
echo "  npm install -g cordova"

echo "\n2) Create a new Cordova project (if you don't have one yet):"
echo "  cordova create myapp com.example.myapp MyApp"

echo "\n3) Change to Cordova project and add Android platform:"
echo "  cd $CORDOVA_PROJECT_DIR"
echo "  cordova platform add android"

echo "\n4) Build debug APK (for testing):"
echo "  cordova build android"
echo "  # Debug APK: $CORDOVA_PROJECT_DIR/platforms/android/app/build/outputs/apk/debug/app-debug.apk"

echo "\n5) (Optional) Install debug APK on connected device via adb:"
echo "  adb install -r $CORDOVA_PROJECT_DIR/platforms/android/app/build/outputs/apk/debug/app-debug.apk"

echo "\n6) Build release (unsigned):"
echo "  cordova build android --release"
echo "  # unsigned APK: $CORDOVA_PROJECT_DIR/platforms/android/app/build/outputs/apk/release/app-release-unsigned.apk"

echo "\n7) Generate a keystore (if you don't have one):"
echo "  keytool -genkey -v -keystore $KEYSTORE_PATH -alias $KEY_ALIAS -keyalg RSA -keysize 2048 -validity 10000"

echo "\n8) Sign the APK using apksigner (recommended):"
echo "  # locate apksigner in your Android SDK build-tools: \
  APKSIGNER=\"\$ANDROID_HOME/build-tools/$ANDROID_SDK_BUILD_TOOLS_VERSION/apksigner\"\n  \$APKSIGNER sign --ks $KEYSTORE_PATH --out app-release-signed.apk app-release-unsigned.apk"

echo "\n9) Align the APK (zipalign):"
echo "  # locate zipalign: \$ANDROID_HOME/build-tools/$ANDROID_SDK_BUILD_TOOLS_VERSION/zipalign\n  zipalign -v -p 4 app-release-signed.apk app-release-aligned.apk"

echo "\n10) Install aligned APK on device (for final smoke test):"
echo "  adb install -r app-release-aligned.apk"

echo "\nNotes:"
echo "  - Prefer HTTPS for API endpoints.\n  - Cordova WebView origin may be file:// or http://localhost depending on plugin; ensure CORS_ALLOW settings in Django allow this.\n  - For modern Android, use 'apksigner' from build-tools (not jarsigner).\n"

exit 0

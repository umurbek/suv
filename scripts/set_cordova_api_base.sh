#!/usr/bin/env bash
# Usage: ./scripts/set_cordova_api_base.sh "https://api.example.com/"
# Replaces API_BASE in cordova_app/www/js/config.js
set -e
if [ -z "$1" ]; then
  echo "Usage: $0 <API_BASE_URL>"
  exit 2
fi
API_BASE="$1"
FILE="cordova_app/www/js/config.js"
if [ ! -f "$FILE" ]; then
  echo "File $FILE not found"
  exit 3
fi
# Create a backup
cp "$FILE" "$FILE.bak"
# Replace the API_BASE line
awk -v api="$API_BASE" 'BEGIN{print "// Cordova template config. Edit API_BASE to your server domain."; print "const API_BASE = \"" api "\";"; print "// For local testing on same LAN, use http://192.168.x.x:8000/\n"; print "// Expose globally for index.html"; print "window.API_BASE = API_BASE;"; exit}' > "$FILE.tmp"
mv "$FILE.tmp" "$FILE"
chmod +x "$FILE"
echo "Updated $FILE with API_BASE=$API_BASE"

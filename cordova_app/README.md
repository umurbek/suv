Cordova mobile app for crm_suv

This folder contains a minimal Cordova web app that can call your Django REST API.

Quick setup
1. Install Cordova and requirements (Node.js+npm required):

   npm install -g cordova

2. Set API base URL used by the web app (replace with your server address):

   ./scripts/set_cordova_api_base.sh "https://api.yourdomain.uz/"

   # For local testing (same LAN) you can use:
   ./scripts/set_cordova_api_base.sh "http://192.168.1.10:8000/"

3. Build the Android app (from project root):

   cd cordova_app
   npm install
   cordova platform add android --no-update
   cordova build android

4. Install on device/emulator:

   adb install -r platforms/android/app/build/outputs/apk/debug/app-debug.apk

Notes
- Ensure your Django server has CORS enabled for the app origin. For dev you can use CORS_ALLOW_ALL_ORIGINS = True in settings.
- The web UI is in `cordova_app/www`.
- `index.html` is a small demo page that sends a POST to the endpoint `/client_panel/api/create_order/`.

Customizing
- Edit `cordova_app/www/index.html` and `cordova_app/www/js/config.js` to add more screens, use token auth, or change API paths.

If you want, I can:
- Copy frontend templates from the Django `templates/` into `cordova_app/www/` and adapt links.
- Implement a small SPA (vanilla JS or a lightweight framework) to match your web UI.
- Add an automated build script that produces a signed release.


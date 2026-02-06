Firebase (FCM) setup for this Cordova app

1) Create Firebase project
   - Go to https://console.firebase.google.com/
   - Create a new project or use existing one

2) Add Android app to project
   - Use applicationId from `cordova_app/config.xml` (widget id), currently `com.example.myapp`.
   - Follow steps and download `google-services.json` when prompted.

3) Place `google-services.json`
   - Put the file at `cordova_app/google-services.json` (project root) OR inside `cordova_app/platforms/android/app/` after platform creation.
   - The `cordova-plugin-firebasex` plugin will look for it during build.

4) Server (backend) FCM server key
   - In Firebase console -> Project settings -> Cloud Messaging -> Server key (legacy)
   - On your Django server set environment variable `FCM_SERVER_KEY` to this key and restart the app. Example (Linux):

```bash
export FCM_SERVER_KEY="AAA...your_server_key_here"
# or add to your systemd/env config
```

5) Build
   - From `cordova_app` folder, install plugins and platform, then build:

```bash
npm install
npx cordova platform add android
npx cordova plugin add cordova-plugin-firebasex
# (other plugins already declared in config.xml will be installed)
npx cordova prepare android
npx cordova build android --release
```

6) Test push
   - In Django admin, ensure `PushToken` entries are created (client devices register token via the app).
   - Use management command from project root:

```bash
./env/bin/python manage.py send_test_push --title "Hello" --body "Test push"
```

Notes:
- For production, prefer Firebase HTTP v1 API and service accounts. This repo uses the legacy server key approach for simplicity.
- Change the Cordova `widget id` in `config.xml` to your real app id before releasing.

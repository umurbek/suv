# Cordova APK yaratuvchi qo'llanma (O'zbekcha)

Quyidagi hujjat Cordova ilovasini serverga bog'lash va APK yaratish uchun to'liq qadamlarni o'z ichiga oladi.

1) Talablar
- Node.js va npm
- Java JDK (OpenJDK 11 yoki 17 tavsiya)
- Android SDK (platform-tools, build-tools)
- adb (Android platform-tools)
- cordova (`npm install -g cordova`)

2) Django tomonida
- `corsheaders` o'rnatilgan va `settings.py` da `corsheaders.middleware.CorsMiddleware` qo'shilgan.
- Devda `CORS_ALLOW_ALL_ORIGINS = True` bo'lishi mumkin, ammo productionda `CORS_ALLOWED_ORIGINS` ni aniq belgilang.
- HTTPS ishlatish tavsiya etiladi.

3) Loyihani sozlash (Cordova)
- `www/js/config.js` faylida `API_BASE` ni o'zgartiring:
```js
const API_BASE = 'https://api.sizningdomen.uz/';
```
- Barcha AJAX/fetch so'rovlarini `API_BASE` orqali yuboring, yoki `www/js/api_client.js` dagi `apiFetch` funktsiyasidan foydalaning.

4) Debug APK yaratish (sinov)
```bash
# Cordova loyihasi katalogiga o'ting yoki yangi yarating
cordova create myapp com.example.myapp MyApp
cd myapp
cordova platform add android
# nusxalash: sizning veb fayllaringizni myapp/www/ ga nusxalang
cordova build android
adb install -r platforms/android/app/build/outputs/apk/debug/app-debug.apk
```

5) Release APK (imzolanmagan) va imzolash
```bash
cordova build android --release
# unsigned APK:
platforms/android/app/build/outputs/apk/release/app-release-unsigned.apk
# Keystore yaratish:
keytool -genkey -v -keystore ~/my-release-key.jks -alias my_alias -keyalg RSA -keysize 2048 -validity 10000
# Keyin skriptlar/dastur yordamida imzolash (apksigner) va zipalign qiling.
```

6) Avtomatlashtirish skriptlar
- `scripts/cordova_create_and_build.sh` — Cordova loyihasini yaratish va debug build uchun yordamchi.
- `scripts/sign_and_align.sh` — unsigned APK ni imzolash va zipalign qilish uchun shablon. Iltimos `KEYSTORE_PATH`, `KEYSTORE_ALIAS`, `BUILD_TOOLS_VERSION` va `ANDROID_SDK_ROOT` ni tekshiring.

7) Muammolar va yechimlar
- Agar tarmoq yoki CORS xatosi bo'lsa, serverdagi `CORS` sozlamalarini tekshiring va ilova originini qo'shing.
- Agar cookie/session ishlamasa (file:// origin), token (JWT) yondashuvini tanlash mumkin.

Agar xohlasangiz, men `www/` ichiga sizning mavjud frontend fayllaringizni moslab qo'yish va Cordova loyihasini to'liq yaratish jarayonini bosqichma-bosqich bajarib bera olaman. Ammo qurilmada build va `apksigner`/`zipalign` bajarish uchun sizning tizimingizda Android SDK va Java o'rnatilgan bo'lishi shart.

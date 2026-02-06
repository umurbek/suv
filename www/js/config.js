// Central API configuration for Cordova app
// Edit the API_BASE value before building the APK.
// For development use local IP (on same network), for production use your HTTPS domain.

// Example (production):
// const API_BASE = 'https://api.sizningdomen.uz/';
// Example (dev on LAN):
// const API_BASE = 'http://192.168.1.10:8000/';

const API_BASE = 'https://api.sizningdomen.uz/';

// Google Maps API key for Cordova webviews. Replace at build-time or keep as
// empty string to require runtime injection from server-side configuration.
// WARNING: Embedding API keys in client-side code can expose them. Prefer
// restricting the key to allowed domains in Google Cloud Console.
const GOOGLE_MAPS_API_KEY = 'AIzaSyDQYQGDSrKUOfwW0PC2Tw7YfdZVWoNqQs0';

export { API_BASE, GOOGLE_MAPS_API_KEY };

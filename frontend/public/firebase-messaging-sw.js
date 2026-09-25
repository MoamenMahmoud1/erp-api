/*
 * Firebase Cloud Messaging service worker for the ERP web app.
 * The Firebase Web SDK config is deliberately loaded from the same-origin
 * public endpoint so no client secret is embedded in this static file.
 */

importScripts(
  "https://www.gstatic.com/firebasejs/12.19.0/firebase-app-compat.js",
  "https://www.gstatic.com/firebasejs/12.19.0/firebase-messaging-compat.js",
);

fetch("/api/v1/notifications/web-config/", {
  credentials: "same-origin",
  cache: "no-store",
})
  .then((response) => {
    if (!response.ok) throw new Error("Unable to load Firebase web config.");
    return response.json();
  })
  .then((config) => {
    if (!config?.enabled) return;

    firebase.initializeApp(config.firebase);
    const messaging = firebase.messaging();

    // FCM automatically displays notification payloads while the app is in
    // the background. Do not render them again here to avoid duplicates.
  })
  .catch(() => {
    // Push delivery is best-effort. The main application still has durable
    // in-app notifications even when the browser push channel is unavailable.
  });

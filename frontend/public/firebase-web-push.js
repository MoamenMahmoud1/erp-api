import { initializeApp } from "https://www.gstatic.com/firebasejs/12.19.0/firebase-app.js";
import {
  getMessaging,
  isSupported,
  onMessage,
  onRegistered,
  onUnregistered,
  register,
  unregister,
} from "https://www.gstatic.com/firebasejs/12.19.0/firebase-messaging.js";

const CONFIG_URL = "/api/v1/notifications/web-config/";

let config = null;
let app = null;
let messaging = null;
let serviceWorkerRegistration = null;
let currentInstallationId = null;
let readyPromise;

function emit(name, detail = {}) {
  window.dispatchEvent(new CustomEvent(name, { detail }));
}

async function loadConfig() {
  const response = await fetch(CONFIG_URL, {
    credentials: "same-origin",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  if (!response.ok) throw new Error("Unable to load Firebase web config.");

  const payload = await response.json();
  if (!payload?.enabled || !payload?.firebase || !payload?.vapid_key) return null;
  return payload;
}

async function initialize() {
  try {
    config = await loadConfig();
    if (!config) return { available: false, permission: getPermission() };

    if (!("serviceWorker" in navigator) || !("Notification" in window)) {
      return { available: false, permission: getPermission() };
    }

    if (!(await isSupported())) {
      return { available: false, permission: getPermission() };
    }

    app = initializeApp(config.firebase);
    messaging = getMessaging(app);

    onRegistered(messaging, (installationId) => {
      currentInstallationId = installationId;
      emit("erp-webpush-registered", {
        installationId,
        firebaseAppId: config.firebase.appId || "",
      });
    });

    onUnregistered(messaging, (installationId) => {
      if (currentInstallationId === installationId) currentInstallationId = null;
      emit("erp-webpush-unregistered", { installationId });
    });

    onMessage(messaging, (payload) => {
      emit("erp-webpush-message", { payload });
    });

    return { available: true, permission: getPermission() };
  } catch (error) {
    emit("erp-webpush-error", { message: String(error?.message || error) });
    return { available: false, permission: getPermission() };
  }
}

function getPermission() {
  return typeof Notification === "undefined" ? "unsupported" : Notification.permission;
}

async function ensureServiceWorker() {
  if (!serviceWorkerRegistration) {
    serviceWorkerRegistration = await navigator.serviceWorker.register("/firebase-messaging-sw.js", {
      scope: "/",
    });
  }
  await navigator.serviceWorker.ready;
  return serviceWorkerRegistration;
}

async function enable({ requestPermission = true } = {}) {
  const state = await readyPromise;
  if (!state.available || !messaging || !config) return { status: "unsupported" };

  let permission = getPermission();
  if (permission !== "granted" && requestPermission) {
    permission = await Notification.requestPermission();
  }

  if (permission !== "granted") return { status: permission };

  const registration = await ensureServiceWorker();
  await register(messaging, {
    vapidKey: config.vapid_key,
    serviceWorkerRegistration: registration,
  });

  return { status: "enabled" };
}

async function disable() {
  await readyPromise;
  const installationId = currentInstallationId;
  if (!messaging) return installationId;

  try {
    await unregister(messaging);
  } catch {
    // The server-side device record is still explicitly deactivated by the app.
  }
  return installationId;
}

readyPromise = initialize();

window.erpWebPush = {
  ready: readyPromise,
  getPermission,
  enable,
  sync: () => enable({ requestPermission: false }),
  disable,
};

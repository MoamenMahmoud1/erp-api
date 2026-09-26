/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string;
  readonly VITE_API_PROXY_TARGET?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

interface ErpWebPushApi {
  ready: Promise<{ available: boolean; permission: NotificationPermission | "unsupported" }>;
  getPermission: () => NotificationPermission | "unsupported";
  enable: (options?: { requestPermission?: boolean }) => Promise<{ status: string }>;
  sync: () => Promise<{ status: string }>;
  disable: () => Promise<string | null>;
}

interface Window {
  erpWebPush?: ErpWebPushApi;
}

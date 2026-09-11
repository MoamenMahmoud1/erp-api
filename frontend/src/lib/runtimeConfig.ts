const configuredApiUrl = import.meta.env.VITE_API_URL?.trim();

export const runtimeConfig = {
  apiBaseUrl: (configuredApiUrl || "/api/v1").replace(/\/$/, ""),
} as const;

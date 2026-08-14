import axios from "axios";

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = axios.create({ baseURL: API_BASE });

api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = window.localStorage.getItem("token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Si el backend devuelve 401 en una petición que SÍ llevaba token (sesión
// caducada o revocada), se limpia la sesión y se manda al login con un
// aviso claro. No se aplica a /api/auth/login ni /api/auth/register: un
// 401 ahí es simplemente "contraseña incorrecta", no una sesión caducada,
// y esas peticiones no llevan token de todas formas.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    const url: string = error?.config?.url || "";
    const isPublicAuthEndpoint = url.includes("/api/auth/login") || url.includes("/api/auth/register");

    if (status === 401 && !isPublicAuthEndpoint && typeof window !== "undefined") {
      clearToken();
      window.sessionStorage.setItem("session_expired", "1");
      if (window.location.pathname !== "/") {
        window.location.href = "/";
      }
    }
    return Promise.reject(error);
  }
);

export function saveToken(token: string) {
  window.localStorage.setItem("token", token);
}

export function clearToken() {
  window.localStorage.removeItem("token");
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem("token");
}

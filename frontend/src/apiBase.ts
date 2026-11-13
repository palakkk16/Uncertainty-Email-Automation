const LOCAL_API = "http://127.0.0.1:8741";

export function apiUrl(path: string): string {
  const configured = import.meta.env.VITE_API_BASE_URL;
  const base =
    typeof configured === "string" ? configured.trim().replace(/\/$/, "") : "";
  if (base) {
    return `${base}${path}`;
  }
  if (import.meta.env.DEV) {
    return path;
  }
  return `${LOCAL_API}${path}`;
}

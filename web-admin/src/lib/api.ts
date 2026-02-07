const API_BASE = import.meta.env.VITE_API_URL;

const csrfCookieName = "csrf_token";

function getCookie(name: string): string | null {
  return document.cookie
    .split(";")
    .map((item) => item.trim())
    .find((item) => item.startsWith(`${name}=`))
    ?.split("=")[1]
    ?.trim() ?? null;
}

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers ?? {});
  const method = options.method?.toUpperCase() ?? "GET";
  if (["POST", "PUT", "PATCH", "DELETE"].includes(method)) {
    const csrfToken = getCookie(csrfCookieName);
    if (csrfToken) {
      headers.set("X-CSRF-Token", decodeURIComponent(csrfToken));
    }
  }
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    credentials: "include",
    headers
  });
  let data: unknown;
  try {
    data = await response.json();
  } catch (error) {
    if (!response.ok) {
      throw new Error(response.statusText);
    }
    throw new Error("Ответ сервера не является JSON.");
  }
  if (!response.ok) {
    const message = (data as { detail?: string }).detail ?? response.statusText;
    throw new Error(message);
  }
  return data as T;
}

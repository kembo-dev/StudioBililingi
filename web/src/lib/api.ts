const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status} ${body}`);
  }
  if (res.status === 204 || res.headers.get("content-length") === "0") {
    return undefined as T;
  }
  const raw = await res.text();
  return (raw ? JSON.parse(raw) : undefined) as T;
}


export function mediaUrl(uri?: string | null): string {
  if (!uri) return "";
  if (/^(https?:|data:|blob:)/.test(uri)) return uri;
  if (uri.startsWith("/")) return `${API}${uri}`;
  return `${API}/${uri}`;
}

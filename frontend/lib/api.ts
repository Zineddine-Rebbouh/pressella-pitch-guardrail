import { EmailPitch } from "@/types";

export function isEmailPitch(
  pitch: EmailPitch | string
): pitch is EmailPitch {
  return typeof pitch === "object" && pitch !== null && "subject" in pitch;
}

export function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

export async function apiFetch<T>(
  url: string,
  opts?: RequestInit
): Promise<{ ok: true; data: T } | { ok: false; status: number; detail: string }> {
  try {
    const res = await fetch(url, opts);
    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try {
        const body = await res.json();
        if (body.detail) detail = body.detail;
      } catch {
        /* no json body */
      }
      return { ok: false, status: res.status, detail };
    }
    const data = (await res.json()) as T;
    return { ok: true, data };
  } catch (err) {
    return {
      ok: false,
      status: 0,
      detail: err instanceof Error ? err.message : "Network error",
    };
  }
}

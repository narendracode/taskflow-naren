import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import type { ApiError } from "@/types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Extract a human-readable error message from an RTK Query error.
 * Handles the various shapes the backend returns.
 */
export function extractErrorMessage(error: unknown): string {
  if (!error || typeof error !== "object") return "An unexpected error occurred";

  const err = error as ApiError;

  // String detail (e.g. 401 "Invalid email or password")
  if (typeof err.data === "string") return err.data;

  if (typeof err.data === "object") {
    const data = err.data;

    // { detail: "string" }
    if (typeof data.detail === "string") return data.detail;

    // { detail: { error: "..." } }
    if (typeof data.detail === "object" && data.detail?.error) {
      return data.detail.error;
    }

    // { error: "..." }
    if (data.error) return data.error;
  }

  return "Something went wrong. Please try again.";
}

/**
 * Extract field-level validation errors from an RTK Query error.
 */
export function extractFieldErrors(
  error: unknown
): Record<string, string> | null {
  if (!error || typeof error !== "object") return null;

  const data = (error as ApiError).data;
  if (typeof data !== "object") return null;

  // { fields: { email: "..." } }
  if (data.fields && Object.keys(data.fields).length > 0) return data.fields;

  // { detail: { fields: { ... } } }
  if (typeof data.detail === "object" && data.detail?.fields) {
    return data.detail.fields ?? null;
  }

  return null;
}

export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function initials(name: string): string {
  return name
    .split(" ")
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase();
}

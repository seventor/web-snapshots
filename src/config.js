import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function defaultConfigPath() {
  if (process.env.CONFIG_PATH) {
    return process.env.CONFIG_PATH;
  }
  return path.resolve(__dirname, "..", "config.json");
}

function normalizePrefix(prefix = "") {
  const normalized = prefix.trim().replace(/^\/+|\/+$/g, "");
  return normalized ? `${normalized}/` : "";
}

export function loadConfig(configPath) {
  const resolvedPath = configPath ?? defaultConfigPath();
  const raw = JSON.parse(readFileSync(resolvedPath, "utf8"));

  const storage = raw.storage ?? {};
  const screenshot = raw.screenshot ?? {};
  const schedule = raw.schedule ?? {};

  const urls = (raw.urls ?? []).map((entry) => {
    const viewport = entry.viewport ?? {};
    return {
      url: entry.url,
      name: entry.name,
      viewportWidth: viewport.width ?? 1920,
      viewportHeight: viewport.height ?? 1080,
      waitMs: entry.waitMs ?? 2000,
      fullPage: Boolean(entry.fullPage),
    };
  });

  return {
    urls,
    screenshotFormat: screenshot.format ?? "jpeg",
    screenshotQuality: screenshot.quality ?? 85,
    s3Bucket: process.env.S3_BUCKET || storage.s3Bucket || "",
    s3Prefix: normalizePrefix(process.env.S3_PREFIX ?? storage.s3Prefix ?? ""),
    publicBaseUrl: (
      process.env.PUBLIC_BASE_URL ||
      storage.publicBaseUrl ||
      "https://snapshots.grense.land"
    ).replace(/\/$/, ""),
    scheduleRateMinutes: schedule.rateMinutes ?? 5,
  };
}

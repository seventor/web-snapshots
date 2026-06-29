import { mkdtemp, rm } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { loadConfig } from "./config.js";
import { captureScreenshots } from "./screenshot.js";
import { persistScreenshots } from "./storage.js";

export async function runTask() {
  const config = loadConfig();
  if (config.urls.length === 0) {
    throw new Error("No URLs configured in config.json");
  }

  const tempDir = await mkdtemp(path.join(os.tmpdir(), "screenshots-"));
  try {
    const files = await captureScreenshots(config, tempDir);
    const publicUrls = await persistScreenshots(config, files);
    return {
      count: publicUrls.length,
      urls: publicUrls,
    };
  } finally {
    await rm(tempDir, { recursive: true, force: true });
  }
}

export async function handler(event) {
  console.log("Starting screenshot task", { event });
  const result = await runTask();
  console.log("Screenshot task completed", result);
  return result;
}

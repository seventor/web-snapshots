import { mkdir } from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";

const USER_AGENT =
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) " +
  "AppleWebKit/537.36 (KHTML, like Gecko) " +
  "Chrome/120.0.0.0 Safari/537.36";

export async function captureScreenshots(config, outputDir) {
  await mkdir(outputDir, { recursive: true });
  const savedPaths = [];

  const browser = await chromium.launch({
    headless: true,
    args: [
      "--no-sandbox",
      "--disable-setuid-sandbox",
      "--disable-dev-shm-usage",
      "--disable-gpu",
    ],
  });

  try {
    for (const target of config.urls) {
      const filePath = path.join(outputDir, `${target.name}.jpg`);
      await captureTarget(browser, target, config, filePath);
      savedPaths.push(filePath);
      console.log(`Captured screenshot for ${target.url} -> ${filePath}`);
    }
  } finally {
    await browser.close();
  }

  return savedPaths;
}

async function captureTarget(browser, target, config, filePath) {
  const context = await browser.newContext({
    viewport: {
      width: target.viewportWidth,
      height: target.viewportHeight,
    },
    userAgent: USER_AGENT,
  });

  const page = await context.newPage();

  try {
    await page.goto(target.url, { waitUntil: "networkidle", timeout: 60_000 });
    if (target.waitMs > 0) {
      await page.waitForTimeout(target.waitMs);
    }
    await page.screenshot({
      path: filePath,
      type: "jpeg",
      quality: config.screenshotQuality,
      fullPage: target.fullPage,
    });
  } finally {
    await context.close();
  }
}

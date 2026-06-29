#!/usr/bin/env node
import path from "node:path";
import { fileURLToPath } from "node:url";
import dotenv from "dotenv";
import { runTask } from "./src/handler.js";

const rootDir = path.dirname(fileURLToPath(import.meta.url));

dotenv.config({ path: path.join(rootDir, ".env") });

process.env.CONFIG_PATH ??= path.join(rootDir, "config.json");
process.env.LOCAL_OUTPUT_DIR ??= path.join(rootDir, "output");

const result = await runTask();

console.log(`Saved ${result.count} screenshot(s):`);
for (const url of result.urls) {
  console.log(`  - ${url}`);
}

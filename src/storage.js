import { copyFile, mkdir } from "node:fs/promises";
import path from "node:path";
import { PutObjectCommand, S3Client } from "@aws-sdk/client-s3";
import { readFile } from "node:fs/promises";

export async function persistScreenshots(config, files) {
  const localOutputDir = process.env.LOCAL_OUTPUT_DIR;
  if (localOutputDir) {
    return saveLocally(config, files, localOutputDir);
  }

  if (!config.s3Bucket) {
    throw new Error(
      "S3_BUCKET is not configured. Set LOCAL_OUTPUT_DIR for local file output.",
    );
  }

  return uploadToS3(config, files);
}

async function saveLocally(config, files, outputDir) {
  const prefixDir = path.join(
    outputDir,
    config.s3Prefix.replace(/^\/+|\/+$/g, ""),
  );
  await mkdir(prefixDir, { recursive: true });
  const publicUrls = [];

  for (const filePath of files) {
    const destination = path.join(prefixDir, path.basename(filePath));
    await copyFile(filePath, destination);
    const publicUrl = `${config.publicBaseUrl}/${path.basename(filePath)}`;
    publicUrls.push(publicUrl);
    console.log(`Saved locally: ${destination}`);
  }

  return publicUrls;
}

async function uploadToS3(config, files) {
  const client = new S3Client({});
  const publicUrls = [];

  for (const filePath of files) {
    const key = `${config.s3Prefix}${path.basename(filePath)}`;
    const body = await readFile(filePath);
    await client.send(
      new PutObjectCommand({
        Bucket: config.s3Bucket,
        Key: key,
        Body: body,
        ContentType: "image/jpeg",
      }),
    );
    const publicUrl = `${config.publicBaseUrl}/${path.basename(filePath)}`;
    publicUrls.push(publicUrl);
    console.log(`Uploaded s3://${config.s3Bucket}/${key}`);
  }

  return publicUrls;
}

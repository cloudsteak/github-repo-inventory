#!/usr/bin/env node
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

const PBKDF2_ITERATIONS = 100_000;

const [, , inputArg, outputArg] = process.argv;
const password = process.env.DASHBOARD_PASSWORD;

if (!password) {
  console.error("DASHBOARD_PASSWORD is required");
  process.exit(1);
}

const inputPath = path.resolve(inputArg ?? path.join("..", "data", "inventory.json"));
const outputPath = path.resolve(outputArg ?? path.join("public", "inventory.enc.json"));

if (!fs.existsSync(inputPath)) {
  console.error(`Input file not found: ${inputPath}`);
  process.exit(1);
}

const plaintext = fs.readFileSync(inputPath);
const salt = crypto.randomBytes(16);
const iv = crypto.randomBytes(12);
const key = crypto.pbkdf2Sync(password, salt, PBKDF2_ITERATIONS, 32, "sha256");
const cipher = crypto.createCipheriv("aes-256-gcm", key, iv);
const encrypted = Buffer.concat([cipher.update(plaintext), cipher.final()]);
const tag = cipher.getAuthTag();

const payload = {
  v: 1,
  salt: salt.toString("base64"),
  iv: iv.toString("base64"),
  ciphertext: Buffer.concat([encrypted, tag]).toString("base64"),
};

fs.mkdirSync(path.dirname(outputPath), { recursive: true });
fs.writeFileSync(outputPath, JSON.stringify(payload));
console.log(`Wrote encrypted inventory to ${outputPath}`);

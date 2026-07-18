import { InventorySnapshot } from "./types";

export const PBKDF2_ITERATIONS = 100_000;

export type EncryptedInventoryPayload = {
  v: number;
  salt: string;
  iv: string;
  ciphertext: string;
};

function fromBase64(value: string): Uint8Array {
  const binary = atob(value);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return bytes;
}

async function deriveKey(password: string, salt: Uint8Array): Promise<CryptoKey> {
  const baseKey = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(password),
    "PBKDF2",
    false,
    ["deriveKey"],
  );
  return crypto.subtle.deriveKey(
    { name: "PBKDF2", salt: salt as BufferSource, iterations: PBKDF2_ITERATIONS, hash: "SHA-256" },
    baseKey,
    { name: "AES-GCM", length: 256 },
    false,
    ["decrypt"],
  );
}

export async function decryptInventory(
  payload: EncryptedInventoryPayload,
  password: string,
): Promise<InventorySnapshot> {
  const salt = fromBase64(payload.salt);
  const iv = fromBase64(payload.iv);
  const ciphertext = fromBase64(payload.ciphertext);
  const key = await deriveKey(password, salt);
  const decrypted = await crypto.subtle.decrypt(
    { name: "AES-GCM", iv: iv as BufferSource },
    key,
    ciphertext as BufferSource,
  );
  return JSON.parse(new TextDecoder().decode(decrypted)) as InventorySnapshot;
}

export class AuthRequiredError extends Error {
  constructor() {
    super("Authentication required");
    this.name = "AuthRequiredError";
  }
}

const LOGIN_PATH = "/__dashboard/login";
const LOGOUT_PATH = "/__dashboard/logout";

export const encryptedInventoryMode = import.meta.env.VITE_ENCRYPTED_INVENTORY === "true";

export async function loginWithServer(password: string): Promise<void> {
  const response = await fetch(LOGIN_PATH, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ password }),
  });
  if (!response.ok) {
    throw new Error("Invalid password");
  }
}

export async function logoutFromServer(): Promise<void> {
  await fetch(LOGOUT_PATH, { method: "POST", credentials: "same-origin" });
}

export async function loadPlainInventory(): Promise<InventorySnapshot> {
  const response = await fetch(`${import.meta.env.BASE_URL}inventory.json`, {
    credentials: "same-origin",
  });
  if (response.status === 401) {
    throw new AuthRequiredError();
  }
  if (!response.ok) {
    throw new Error(
      response.status === 404
        ? "inventory.json not found. Run: uv run github-repo-inventory sync"
        : `Failed to load inventory.json (${response.status})`,
    );
  }

  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) {
    throw new Error(
      "inventory.json returned HTML instead of JSON. Restart the dev server from dashboard/ after syncing.",
    );
  }

  return response.json();
}

export async function loadEncryptedInventory(password: string): Promise<InventorySnapshot> {
  const response = await fetch(`${import.meta.env.BASE_URL}inventory.enc.json`);
  if (!response.ok) {
    throw new Error("Encrypted inventory not found. Redeploy the dashboard.");
  }

  const payload = (await response.json()) as EncryptedInventoryPayload;
  try {
    return await decryptInventory(payload, password);
  } catch {
    throw new Error("Invalid password");
  }
}

import crypto from "node:crypto";
import type { IncomingMessage, ServerResponse } from "node:http";
import type { Connect } from "vite";

export const AUTH_COOKIE = "dashboard_session";
export const LOGIN_PATH = "/__dashboard/login";
export const LOGOUT_PATH = "/__dashboard/logout";

export function sessionToken(password: string): string {
  return crypto.createHash("sha256").update(`dashboard:${password}`).digest("hex");
}

function parseCookies(header: string | undefined): Record<string, string> {
  if (!header) return {};
  return Object.fromEntries(
    header.split(";").map((part) => {
      const [key, ...rest] = part.trim().split("=");
      return [key, decodeURIComponent(rest.join("="))];
    }),
  );
}

export function isAuthenticated(req: IncomingMessage, password: string | undefined): boolean {
  if (!password) return true;
  const cookies = parseCookies(req.headers.cookie);
  return cookies[AUTH_COOKIE] === sessionToken(password);
}

function readJsonBody(req: IncomingMessage): Promise<unknown> {
  return new Promise((resolve, reject) => {
    let data = "";
    req.on("data", (chunk) => {
      data += chunk;
    });
    req.on("end", () => {
      try {
        resolve(data ? JSON.parse(data) : {});
      } catch (error) {
        reject(error);
      }
    });
    req.on("error", reject);
  });
}

function setSessionCookie(res: ServerResponse, password: string): void {
  res.setHeader(
    "Set-Cookie",
    `${AUTH_COOKIE}=${sessionToken(password)}; Path=/; HttpOnly; SameSite=Strict`,
  );
}

function clearSessionCookie(res: ServerResponse): void {
  res.setHeader("Set-Cookie", `${AUTH_COOKIE}=; Path=/; Max-Age=0; HttpOnly; SameSite=Strict`);
}

function sendJson(res: ServerResponse, statusCode: number, payload: unknown): void {
  res.statusCode = statusCode;
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.end(JSON.stringify(payload));
}

function requestPath(url: string | undefined): string {
  return (url ?? "/").split("?")[0] || "/";
}

export function protectInventoryPath(pathname: string): boolean {
  return pathname === "/inventory.json" || pathname.endsWith("/inventory.json");
}

export function installDashboardAuth(
  middlewares: Connect.Server,
  password: string | undefined,
): void {
  if (!password) return;

  middlewares.use(async (req, res, next) => {
    const pathname = requestPath(req.url);

    if (pathname === LOGIN_PATH && req.method === "POST") {
      try {
        const body = (await readJsonBody(req)) as { password?: string };
        if (body.password !== password) {
          sendJson(res, 401, { error: "Invalid password" });
          return;
        }
        setSessionCookie(res, password);
        sendJson(res, 200, { ok: true });
      } catch {
        sendJson(res, 400, { error: "Invalid request" });
      }
      return;
    }

    if (pathname === LOGOUT_PATH && req.method === "POST") {
      clearSessionCookie(res);
      sendJson(res, 200, { ok: true });
      return;
    }

    if (protectInventoryPath(pathname) && !isAuthenticated(req, password)) {
      res.statusCode = 401;
      res.setHeader("Content-Type", "text/plain; charset=utf-8");
      res.end("Unauthorized");
      return;
    }

    next();
  });
}

import fs from "node:fs";
import path from "node:path";
import { defineConfig, loadEnv, type Plugin } from "vite";
import react from "@vitejs/plugin-react";
import { installDashboardAuth, isAuthenticated, protectInventoryPath } from "./vite-auth";

function dashboardServerPlugin(dashboardPassword: string | undefined): Plugin {
  return {
    name: "dashboard-server",
    configureServer(server) {
      installDashboardAuth(server.middlewares, dashboardPassword);
      server.middlewares.use((req, res, next) => {
        const pathname = (req.url ?? "/").split("?")[0] || "/";
        if (!protectInventoryPath(pathname)) {
          next();
          return;
        }
        if (!isAuthenticated(req, dashboardPassword)) {
          next();
          return;
        }
        const inventoryPath = path.resolve(server.config.root, "../data/inventory.json");
        if (!fs.existsSync(inventoryPath)) {
          res.statusCode = 404;
          res.setHeader("Content-Type", "text/plain; charset=utf-8");
          res.end("inventory.json not found. Run: uv run github-repo-inventory sync");
          return;
        }
        res.setHeader("Content-Type", "application/json; charset=utf-8");
        fs.createReadStream(inventoryPath).pipe(res);
      });
    },
    configurePreviewServer(server) {
      installDashboardAuth(server.middlewares, dashboardPassword);
    },
  };
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, path.resolve(__dirname, ".."), "");
  const dashboardPassword = env.DASHBOARD_PASSWORD || undefined;

  return {
    plugins: [react(), dashboardServerPlugin(dashboardPassword)],
    base: "./",
    envDir: path.resolve(__dirname, ".."),
    // Only VITE_* vars are exposed to browser code. DASHBOARD_PASSWORD stays server/CI-only.
    envPrefix: ["VITE_"],
    server: {
      fs: {
        allow: [".."],
      },
    },
  };
});

import fs from "node:fs";
import path from "node:path";
import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";

function inventoryJsonDevServer(): Plugin {
  return {
    name: "inventory-json-dev-server",
    configureServer(server) {
      server.middlewares.use("/inventory.json", (_req, res) => {
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
  };
}

export default defineConfig({
  plugins: [react(), inventoryJsonDevServer()],
  base: "./",
  server: {
    fs: {
      allow: [".."],
    },
  },
});

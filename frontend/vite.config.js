import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig(function (_a) {
    var mode = _a.mode;
    var env = loadEnv(mode, ".", "");
    var backendUrl = env.VITE_BACKEND_URL || "http://localhost:8000";
    return {
        plugins: [react()],
        server: {
            host: "0.0.0.0",
            port: 3000,
            proxy: {
                "/api": {
                    target: backendUrl,
                    changeOrigin: true,
                },
                "/screenshots": {
                    target: backendUrl,
                    changeOrigin: true,
                },
            },
        },
    };
});

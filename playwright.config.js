const os = require("os");
const path = require("path");
const { defineConfig } = require("@playwright/test");

const repoRoot = __dirname;
const dataDir = path.join(os.tmpdir(), "winds-ledger-playwright");
const pythonExe = path.join(repoRoot, ".venv", "Scripts", "python.exe");
const serverScript = path.join(repoRoot, "backend", "tests", "support", "run_e2e_server.py");
const host = "127.0.0.1";
const port = 4173;

process.env.WINDS_LEDGER_E2E_DATA_DIR = dataDir;

module.exports = defineConfig({
    testDir: "./e2e",
    timeout: 120000,
    expect: {
        timeout: 15000,
    },
    fullyParallel: false,
    workers: 1,
    reporter: "list",
    use: {
        baseURL: `http://${host}:${port}`,
        browserName: "firefox",
        headless: true,
    },
    webServer: {
        command: `"${pythonExe}" "${serverScript}"`,
        cwd: repoRoot,
        url: `http://${host}:${port}/api/health`,
        timeout: 120000,
        reuseExistingServer: false,
        env: {
            WINDS_LEDGER_E2E_DATA_DIR: dataDir,
            WINDS_LEDGER_E2E_HOST: host,
            WINDS_LEDGER_E2E_PORT: String(port),
            PYTHONUNBUFFERED: "1",
        },
    },
});
/**
 * @fileoverview Verify Windows server replacement, shutdown, and process isolation.
 * @license Apache-2.0
 * @copyright 2026 Timothy Mallory
 */
const assert = require("node:assert/strict");
const { spawn, spawnSync } = require("node:child_process");
const fs = require("node:fs");
const http = require("node:http");
const net = require("node:net");
const path = require("node:path");
const { setTimeout: delay } = require("node:timers/promises");
const test = require("node:test");

const root = path.resolve(__dirname, "..");

function getHealth(port) {
  return new Promise((resolve, reject) => {
    const request = http.get(`http://127.0.0.1:${port}/api/health`, (response) => {
      let body = "";
      response.setEncoding("utf8");
      response.on("data", (chunk) => { body += chunk; });
      response.on("end", () => {
        try {
          assert.equal(response.statusCode, 200);
          resolve(JSON.parse(body));
        } catch (error) { reject(error); }
      });
    });
    request.setTimeout(1000, () => request.destroy(new Error("Health request timed out")));
    request.on("error", reject);
  });
}

async function reservePort() {
  const listener = net.createServer();
  await new Promise((resolve, reject) => {
    listener.once("error", reject);
    listener.listen(0, "127.0.0.1", resolve);
  });
  return listener;
}

function runBatch(name, env) {
  const result = spawnSync("cmd.exe", ["/d", "/c", path.join(root, name)], {
    cwd: root, env, encoding: "utf8", windowsHide: true, timeout: 30000,
  });
  if (result.error) throw result.error;
  return result;
}

async function waitForExit(child) {
  const deadline = Date.now() + 15000;
  while (child.exitCode === null && Date.now() < deadline) await delay(100);
  assert.notEqual(child.exitCode, null, "Launcher must exit");
}

async function waitForHealth(port, databasePath) {
  const deadline = Date.now() + 30000;
  while (Date.now() < deadline) {
    try {
      const health = await getHealth(port);
      assert.equal(path.resolve(health.database_path), databasePath);
      return;
    } catch { await delay(250); }
  }
  throw new Error(`Backend on port ${port} did not become ready with its isolated database`);
}

function assertProcessStopped(pid) {
  assert.throws(() => process.kill(pid, 0), { code: "ESRCH" });
}

test("startup replaces its hidden server tree and shutdown preserves other instances", {
  skip: process.platform !== "win32", timeout: 120000,
}, async () => {
  const outputs = path.join(root, "outputs");
  fs.mkdirSync(outputs, { recursive: true });
  const testDir = fs.mkdtempSync(path.join(outputs, "startup-lifecycle-"));
  const environments = [];
  const launchers = [];
  const reservations = [];
  let logNumber = 0;

  function environment(port, suffix) {
    const dataDir = path.join(testDir, suffix);
    const env = {
      ...process.env,
      TIMS_LEDGER_HOST: "127.0.0.1",
      TIMS_LEDGER_PORT: String(port),
      TIMS_LEDGER_FOREGROUND: "1",
      TIMS_LEDGER_SKIP_BROWSER: "1",
      TIMS_LEDGER_DATA_DIR: dataDir,
      TIMS_LEDGER_DB_PATH: path.join(dataDir, "tims-ledger.db"),
      TIMS_LEDGER_MIGRATIONS_DIR: path.join(root, "migrations"),
      TIMS_LEDGER_SKIP_STARTUP_MIGRATIONS: "0",
      TIMS_LEDGER_WINDOW_TITLE: "Tim's Ledger startup verification",
    };
    environments.push(env);
    return env;
  }

  function startHidden(env) {
    const logPath = path.join(testDir, `launcher-${++logNumber}.log`);
    const logFd = fs.openSync(logPath, "w");
    let child;
    try {
      child = spawn("cmd.exe", ["/d", "/c", path.join(root, "startup.bat")], {
        cwd: root, env, windowsHide: true, stdio: ["ignore", logFd, logFd],
      });
    } finally { fs.closeSync(logFd); }
    launchers.push(child);
    return { child, logPath };
  }

  try {
    for (let index = 0; index < 3; index++) reservations.push(await reservePort());
    const [portA, portB, portC] = reservations.map((listener) => listener.address().port);
    const envA = environment(portA, "first-data");
    const envB = environment(portB, "other-port-data");
    const envC = environment(portC, "unrelated-port-data");
    await Promise.all(reservations.slice(0, 2).map((listener) =>
      new Promise((resolve) => listener.close(resolve))));

    const first = startHidden(envA);
    await waitForHealth(portA, envA.TIMS_LEDGER_DB_PATH);
    const oldLog = fs.readFileSync(first.logPath, "utf8");
    const oldReloader = Number(oldLog.match(/Started reloader process \[(\d+)\]/)[1]);
    const oldWorker = Number(oldLog.match(/Started server process \[(\d+)\]/)[1]);

    startHidden(envB);
    await waitForHealth(portB, envB.TIMS_LEDGER_DB_PATH);

    // Exercise the normal launcher after a hidden foreground instance.
    const restarted = startHidden({ ...envA, TIMS_LEDGER_FOREGROUND: "0" });
    await waitForExit(first.child);
    await waitForExit(restarted.child);
    const restartLog = fs.readFileSync(restarted.logPath, "utf8");
    assert.equal(restarted.child.exitCode, 0, restartLog);
    assert.match(restartLog, /Stopping existing Tim's Ledger backend/);
    await waitForHealth(portA, envA.TIMS_LEDGER_DB_PATH);
    await delay(100);
    assertProcessStopped(oldReloader);
    assertProcessStopped(oldWorker);
    assert.notEqual(first.child.exitCode, null, "Old foreground launcher must exit");
    await waitForHealth(portB, envB.TIMS_LEDGER_DB_PATH);

    const stopped = runBatch("shutdown.bat", envA);
    assert.equal(stopped.status, 0, stopped.stdout + stopped.stderr);
    await assert.rejects(getHealth(portA));
    await waitForHealth(portB, envB.TIMS_LEDGER_DB_PATH);
    assert.equal(runBatch("shutdown.bat", envA).status, 0, "Repeated shutdown must be harmless");

    const conflict = runBatch("startup.bat", envC);
    assert.equal(conflict.status, 1, conflict.stdout + conflict.stderr);
    assert.match(conflict.stdout, /Port \d+ is still in use/);
    assert.equal(reservations[2].listening, true, "Unrelated listener must survive");
  } catch (error) {
    for (const file of fs.readdirSync(testDir).filter((name) => name.endsWith(".log"))) {
      error.message += `\n${file}:\n${fs.readFileSync(path.join(testDir, file), "utf8")}`;
    }
    throw error;
  } finally {
    const cleanupErrors = [];
    for (const listener of reservations) {
      if (listener.listening) await new Promise((resolve) => listener.close(resolve));
    }
    for (const env of environments) {
      try {
        const stopped = runBatch("shutdown.bat", env);
        assert.equal(stopped.status, 0, stopped.stdout + stopped.stderr);
      } catch (error) { cleanupErrors.push(error); }
    }
    for (const child of launchers) {
      if (child.exitCode === null) {
        spawnSync("taskkill.exe", ["/PID", String(child.pid), "/T", "/F"], { windowsHide: true });
      }
    }
    for (const env of environments) {
      try { await assert.rejects(getHealth(Number(env.TIMS_LEDGER_PORT))); }
      catch (error) { cleanupErrors.push(error); }
    }
    if (cleanupErrors.length) throw new AggregateError(cleanupErrors, "Test server cleanup failed");
    assert.ok(path.resolve(testDir).startsWith(path.resolve(outputs) + path.sep));
    fs.rmSync(testDir, { recursive: true, force: true });
  }
});

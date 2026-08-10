import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { resolve } from "node:path";

const python = process.platform === "win32"
  ? resolve(".venv/Scripts/python.exe")
  : resolve(".venv/bin/python");
if (!existsSync(python)) {
  console.error("Run setup before development.");
  process.exit(2);
}

const npm = process.platform === "win32" ? "npm.cmd" : "npm";
const children = [
  spawn(python, ["-m", "uvicorn", "personal_os.interfaces.http.app:app", "--reload", "--host", "127.0.0.1", "--port", "8000"], {
    stdio: "inherit",
    env: process.env
  }),
  spawn(npm, ["--workspace", "frontend", "run", "dev"], {
    stdio: "inherit",
    env: process.env
  })
];

const stop = () => children.forEach((child) => child.kill());
process.on("SIGINT", stop);
process.on("SIGTERM", stop);
children.forEach((child) => child.on("exit", (code) => {
  if (code && code !== 0) {
    stop();
    process.exitCode = code;
  }
}));

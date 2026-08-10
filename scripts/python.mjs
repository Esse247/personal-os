import { existsSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { resolve } from "node:path";

const candidates = process.platform === "win32"
  ? [resolve(".venv/Scripts/python.exe")]
  : [resolve(".venv/bin/python")];

if (process.env.PERSONAL_OS_PYTHON) {
  candidates.unshift(process.env.PERSONAL_OS_PYTHON);
}

const executable = candidates.find((candidate) => existsSync(candidate));
if (!executable) {
  console.error("Python environment not found. Run the documented setup command first.");
  process.exit(2);
}

const result = spawnSync(executable, process.argv.slice(2), {
  cwd: process.cwd(),
  env: process.env,
  stdio: "inherit"
});

if (result.error) {
  console.error(result.error.message);
  process.exit(1);
}

process.exit(result.status ?? 1);

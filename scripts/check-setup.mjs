import { existsSync } from "node:fs";
import { resolve } from "node:path";

const python = process.platform === "win32"
  ? resolve(".venv/Scripts/python.exe")
  : resolve(".venv/bin/python");
const required = [python, resolve("node_modules"), resolve("node_modules/react")];
const missing = required.filter((path) => !existsSync(path));

if (missing.length) {
  console.error(`Setup incomplete. Missing:\n${missing.join("\n")}`);
  process.exit(1);
}

console.log("PERSONAL OS local dependencies are present.");

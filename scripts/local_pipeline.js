import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");

function run(command, args, description) {
  console.log(`\n==> ${description}`);
  const result = spawnSync(command, args, {
    cwd: root,
    stdio: "inherit",
  });

  if (result.error) {
    throw result.error;
  }
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

function findPython() {
  const candidates =
    process.platform === "win32"
      ? [["py", "-3"], ["python", null], ["python3", null]]
      : [["python3", null], ["python", null], ["py", "-3"]];

  for (const [command, fixedArg] of candidates) {
    const args = fixedArg ? [fixedArg, "-c", "pass"] : ["-c", "pass"];
    const result = spawnSync(command, args, { stdio: "ignore" });
    if (!result.error && result.status === 0) {
      return { command, fixedArg };
    }
  }

  throw new Error("Python 3 is required. Install Python 3.14 and try again.");
}

const python = findPython();
const pythonArgs = (args) =>
  python.fixedArg ? [python.fixedArg, ...args] : args;
const npm = process.platform === "win32" ? "npm.cmd" : "npm";

run(python.command, pythonArgs(["-m", "pip", "install", "--upgrade", "pip"]), "Updating pip");
run(python.command, pythonArgs(["-m", "pip", "install", "pytest"]), "Installing pytest");

const requirements = resolve(root, "backend", "requirements.txt");
if (existsSync(requirements)) {
  run(
    python.command,
    pythonArgs(["-m", "pip", "install", "-r", requirements]),
    "Installing backend dependencies",
  );
}

run(python.command, pythonArgs(["-m", "pytest", "backend/tests"]), "Running backend tests");
run(npm, ["ci", "--prefix", "frontend"], "Installing frontend dependencies");
run(npm, ["run", "build", "--prefix", "frontend"], "Building frontend");

console.log("\nLocal CI completed successfully.");

import { parseArgs } from "node:util";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";
import { resolve, join } from "node:path";
import { homedir } from "node:os";
import { mkdirSync, readFileSync, writeFileSync, statSync, existsSync } from "node:fs";
import { privatePath } from "./paths.mjs";

const { values } = parseArgs({
  options: {
    checkout: { type: "string" },
    input: { type: "string" },
    output: { type: "string" },
    fallback: { type: "string" },
  },
});
if (["checkout", "input", "output", "fallback"].some((key) => !values[key]))
  throw new Error("Required: --checkout --input --output --fallback");
const output = privatePath(values.output),
  fallback = privatePath(values.fallback),
  input = resolve(values.input);
if (existsSync(output))
  throw new Error("Choose a new output directory; existing exports are never overwritten");
const checkout = resolve(values.checkout);
const require = createRequire(join(checkout, "apps/server/package.json"));
const Effect = await import(pathToFileURL(require.resolve("effect/Effect")));
const NodeServices = await import(
  pathToFileURL(require.resolve("@effect/platform-node/NodeServices"))
);
const { readAntigravitySession } = await import(
  pathToFileURL(join(checkout, "apps/server/src/project/AntigravitySessionReader.ts"))
);
const { decodeAntigravityTrajectory } = await import(
  pathToFileURL(join(checkout, "apps/server/src/project/AntigravityTranscript.ts"))
);
const report = JSON.parse(readFileSync(join(input, "export-report.json"), "utf8"));
if (!Array.isArray(report)) throw new Error("Invalid export report");
mkdirSync(output, { recursive: true });
mkdirSync(fallback, { recursive: true });
const results = [];
const directoryExists = (path) => {
  try {
    return statSync(path).isDirectory();
  } catch {
    return false;
  }
};
for (const entry of report) {
  if (!/^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(entry.id))
    throw new Error("Invalid export identity");
  try {
    let trajectory;
    if (entry.error === null) {
      const file = join(input, "conversations", entry.id + ".trajectory.json");
      if (statSync(file).size > 128 * 1024 * 1024) throw new Error("Export too large");
      trajectory = JSON.parse(readFileSync(file, "utf8"));
    } else {
      if (typeof entry.source !== "string" || !entry.source.endsWith(".db"))
        throw new Error("Encrypted history requires the local service");
      const session = await Effect.runPromise(
        readAntigravitySession(entry.source).pipe(Effect.provide(NodeServices.layer)),
      );
      trajectory = {
        cascadeId: session.sessionId,
        metadata: {
          ...(session.createdAt ? { createdAt: session.createdAt } : {}),
          workspaces: session.paths.map((path) => ({
            workspaceFolderAbsoluteUri: pathToFileURL(path).href,
          })),
        },
        steps: session.messages.map((message) => ({
          type:
            message.role === "user"
              ? "CORTEX_STEP_TYPE_USER_INPUT"
              : "CORTEX_STEP_TYPE_PLANNER_RESPONSE",
          metadata: { createdAt: message.createdAt },
          ...(message.role === "user"
            ? { userInput: { userResponse: message.text } }
            : { plannerResponse: { response: message.text } }),
        })),
      };
    }
    const decoded = decodeAntigravityTrajectory(trajectory);
    if (decoded.sessionId !== entry.id) throw new Error("Identity mismatch");
    const useFallback =
      decoded.paths.length !== 1 ||
      !directoryExists(decoded.paths[0]) ||
      resolve(decoded.paths[0]) === homedir();
    trajectory.t3Import = {
      workspaceRoot: useFallback ? fallback : decoded.paths[0],
      originalWorkspacePaths: decoded.paths,
      continuation: "new-session",
    };
    writeFileSync(join(output, entry.id + ".trajectory.json"), JSON.stringify(trajectory), {
      flag: "wx",
    });
    results.push({
      id: entry.id,
      messages: decoded.messages.length,
      fallback: useFallback,
      error: null,
    });
  } catch {
    results.push({
      id: entry.id,
      error: "Could not prepare; check format, identity, timestamps, and size limits",
    });
  }
}
writeFileSync(join(output, "preparation-report.json"), JSON.stringify(results, null, 2), {
  flag: "wx",
});
const failed = results.filter((result) => result.error !== null).length;
console.log(
  JSON.stringify({
    prepared: results.length - failed,
    failed,
    messages: results.reduce((n, r) => n + (r.messages ?? 0), 0),
  }),
);
if (failed) process.exitCode = 1;

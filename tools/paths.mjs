import { existsSync, realpathSync } from "node:fs";
import { basename, dirname, isAbsolute, join, relative, resolve, sep } from "node:path";
import { homedir } from "node:os";
import { fileURLToPath } from "node:url";

function canonical(path) {
  let parent = resolve(path);
  const parts = [];
  while (!existsSync(parent)) {
    parts.unshift(basename(parent));
    const next = dirname(parent);
    if (next === parent) throw new Error("Cannot resolve output directory");
    parent = next;
  }
  return join(realpathSync(parent), ...parts);
}

function inside(base, target) {
  const path = relative(base, target);
  return !path || (path !== ".." && !path.startsWith(".." + sep) && !isAbsolute(path));
}

export function privatePath(value) {
  const path = canonical(value);
  const repository = canonical(fileURLToPath(new URL("..", import.meta.url)));
  if (inside(repository, path) || inside(canonical(join(homedir(), ".gemini")), path)) {
    throw new Error("Choose an output outside this repository and the original Antigravity store");
  }
  return path;
}

import { test } from "node:test";
import { strict as assert } from "node:assert";
import { fileURLToPath } from "node:url";
import { homedir, tmpdir } from "node:os";
import { join } from "node:path";
import { privatePath } from "../tools/paths.mjs";

test("rejects repository output including dot-prefixed directories", () => {
  const repository = fileURLToPath(new URL("..", import.meta.url));
  assert.throws(() => privatePath(join(repository, "exports")));
  assert.throws(() => privatePath(join(repository, "..private-exports")));
  assert.throws(() => privatePath(join(homedir(), ".gemini", "exports")));
});

test("accepts a private directory outside the source tree", () => {
  assert.ok(
    privatePath(join(tmpdir(), "synthetic-antigravity-export")).endsWith(
      "synthetic-antigravity-export",
    ),
  );
});

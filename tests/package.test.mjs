import { test } from "node:test";
import { strict as assert } from "node:assert";
import { createRequire } from "node:module";
import { pathToFileURL, fileURLToPath } from "node:url";
import { join, dirname } from "node:path";
import { createHash } from "node:crypto";
import {
  mkdtempSync,
  mkdirSync,
  writeFileSync,
  readFileSync,
  statSync,
  createReadStream,
  symlinkSync,
  rmSync,
} from "node:fs";
import { spawnSync } from "node:child_process";

test(
  "packages synthetic app files and preserves native dependency bytes",
  {
    skip:
      process.platform !== "win32" || !process.env.T3_IMPORT_TEST_CHECKOUT
        ? "Requires Windows and a patched checkout with installed dependencies"
        : false,
  },
  async () => {
    const realCheckout = process.env.T3_IMPORT_TEST_CHECKOUT;
    const require = createRequire(join(realCheckout, "scripts/package.json"));
    const asar = await import(pathToFileURL(require.resolve("@electron/asar")));
    const root = mkdtempSync(
      join(fileURLToPath(new URL("../..", import.meta.url)), "synthetic-agy-package-"),
    );
    try {
      const checkout = join(root, "checkout"),
        resources = join(root, "installation/resources");
      mkdirSync(resources, { recursive: true });
      const write = (relative, contents) => {
        const path = join(checkout, relative);
        mkdirSync(join(path, ".."), { recursive: true });
        writeFileSync(path, contents);
        return path;
      };
      write("scripts/package.json", "{}");
      mkdirSync(join(checkout, "scripts/node_modules/@electron"), { recursive: true });
      symlinkSync(
        dirname(dirname(require.resolve("@electron/asar"))),
        join(checkout, "scripts/node_modules/@electron/asar"),
        "junction",
      );
      write("apps/server/package.json", JSON.stringify({ version: "0.1.3" }));
      write("apps/server/dist/bin.mjs", 'console.log("synthetic updated server");');
      write("apps/server/dist/client/index.html", "<html>Synthetic client</html>");
      const app = write("fixture-app.json", JSON.stringify({ version: "0.1.3" }));
      const old = write("fixture-server.mjs", 'console.log("synthetic original server");');
      const native = write("fixture-native.bin", "MZ synthetic native dependency; never executed");
      const stream = (path, file, unpacked = false) => ({
        path,
        type: "file",
        stat: statSync(file),
        streamGenerator: () => createReadStream(file),
        unpacked,
      });
      await asar.createPackageFromStreams(join(resources, "app.asar"), [
        stream("package.json", app),
      ]);
      await asar.createPackageFromStreams(join(resources, "server.asar"), [
        stream("apps/server/dist/bin.mjs", old),
        stream("node_modules/synthetic/addon.node", native, true),
      ]);
      const output = join(root, "bundle");
      const script = fileURLToPath(new URL("../scripts/package-windows.mjs", import.meta.url));
      const result = spawnSync(
        process.execPath,
        [script, "--checkout", checkout, "--resources", resources, "--output", output],
        { encoding: "utf8", windowsHide: true },
      );
      assert.equal(result.status, 0, result.stderr);
      const archive = join(output, "server.asar");
      assert.match(
        asar.extractFile(archive, join("apps/server/dist/bin.mjs")).toString(),
        /updated server/,
      );
      assert.match(
        asar.extractFile(archive, join("apps/server/dist/client/index.html")).toString(),
        /Synthetic client/,
      );
      assert.deepEqual(
        readFileSync(join(archive + ".unpacked", "node_modules/synthetic/addon.node")),
        readFileSync(native),
      );
      const manifest = JSON.parse(readFileSync(join(output, "manifest.json"), "utf8"));
      const hash = (file) => createHash("sha256").update(readFileSync(file)).digest("hex");
      assert.equal(manifest.updatedSha256, hash(archive));
      assert.equal(manifest.originalSha256, hash(join(resources, "server.asar")));
    } finally {
      // Only this test's freshly created temporary directory is removed.
      assert.ok(
        root.startsWith(
          join(fileURLToPath(new URL("../..", import.meta.url)), "synthetic-agy-package-"),
        ),
      );
      rmSync(root, { recursive: true, force: true });
    }
  },
);

import { parseArgs } from "node:util";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";
import { resolve, join, relative, sep } from "node:path";
import { createHash } from "node:crypto";
import {
  mkdirSync,
  existsSync,
  readFileSync,
  writeFileSync,
  readdirSync,
  lstatSync,
  readlinkSync,
  createReadStream,
} from "node:fs";
import { privatePath } from "../tools/paths.mjs";

const { values } = parseArgs({
  options: {
    checkout: { type: "string" },
    resources: { type: "string" },
    output: { type: "string" },
  },
});
if (!values.checkout || !values.output)
  throw new Error("Required: --checkout --output; optional: --resources");
if (process.platform !== "win32" || process.arch !== "x64")
  throw new Error("Only Windows x64 has been validated");
const checkout = resolve(values.checkout),
  output = privatePath(values.output);
if (existsSync(output)) throw new Error("Choose a new output folder");
const resources = resolve(
  values.resources ?? join(process.env.LOCALAPPDATA, "Programs/t3code/resources"),
);
const installed = join(resources, "server.asar");
const require = createRequire(join(checkout, "scripts/package.json"));
const asar = await import(pathToFileURL(require.resolve("@electron/asar")));
const installedVersion = JSON.parse(
  asar.extractFile(join(resources, "app.asar"), "package.json").toString(),
).version;
const sourceVersion = JSON.parse(
  readFileSync(join(checkout, "apps/server/package.json"), "utf8"),
).version;
if (installedVersion !== sourceVersion || sourceVersion !== "0.1.3")
  throw new Error("This patch requires the matching T3 0.1.3 installation");
mkdirSync(output, { recursive: true });
const source = join(output, "server-source");
asar.extractAll(installed, source);
// Build a new file list instead of deleting anything from an extracted install.
const prefix = "apps/server/dist";
const nativeFiles = [];
function collect(tree, prefix = "") {
  for (const [name, entry] of Object.entries(tree.files ?? {})) {
    const path = prefix ? prefix + "/" + name : name;
    if (entry.files) collect(entry, path);
    else if (entry.unpacked) nativeFiles.push(path);
  }
}
collect(asar.getRawHeader(installed).header);
const streams = [];
function add(directory, base, excludeDist = false) {
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const file = join(directory, entry.name),
      path = relative(base, file).split(sep).join("/");
    if (excludeDist && (path === prefix || path.startsWith(prefix + "/"))) continue;
    const target = excludeDist ? path : prefix + "/" + path;
    const stat = lstatSync(file);
    if (entry.isDirectory()) {
      streams.push({ path: target, type: "directory", stat });
      add(file, base, excludeDist);
    } else if (entry.isSymbolicLink()) {
      streams.push({
        path: target,
        type: "link",
        stat,
        symlink: readlinkSync(file),
        unpacked: nativeFiles.includes(target),
      });
    } else
      streams.push({
        path: target,
        type: "file",
        stat,
        streamGenerator: () => createReadStream(file),
        unpacked: nativeFiles.includes(target),
      });
  }
}
const dist = join(checkout, prefix);
if (!existsSync(join(dist, "client/index.html")))
  throw new Error("Build the server and its client first");
add(source, source, true);
add(dist, dist);
const archive = join(output, "server.asar");
await asar.createPackageFromStreams(archive, streams);
const digest = (file) => createHash("sha256").update(readFileSync(file)).digest("hex");
const nativeHashes = {};
for (const file of nativeFiles) {
  const before = digest(join(installed + ".unpacked", file));
  if (before !== digest(join(archive + ".unpacked", file)))
    throw new Error("Native dependency changed");
  nativeHashes[file] = before;
}
for (const entry of ["bin.mjs", "client/index.html"]) {
  if (!asar.extractFile(archive, join(prefix, entry)).equals(readFileSync(join(dist, entry))))
    throw new Error("Stale bundle");
}
writeFileSync(
  join(output, "manifest.json"),
  JSON.stringify(
    {
      version: sourceVersion,
      originalSha256: digest(installed),
      updatedSha256: digest(archive),
      nativeHashes,
    },
    null,
    2,
  ),
);
console.log("Packaged local update. Native dependencies match the original installation.");

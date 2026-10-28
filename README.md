# Antigravity history import for T3 Code

Bring local Antigravity conversations into T3 Code through its existing project-import flow.

**Experimental · Windows x64 · Source patch, not an official T3 release**

This repository contains a patch for a pinned T3 revision and local export/build tools.
It contains **no real conversations, credentials, installed application files, or prebuilt binaries**.
It is not affiliated with T3 Tools or Google.

## What it does

- Discovers Antigravity SQLite history and local trajectory exports.
- Imports user and assistant text, including older conversations and histories longer than 200 messages.
- Preserves message timestamps and marks omitted attachments.
- Uses T3's existing import records to avoid duplicating unchanged imports.
- Adds **Settings → General → Import history** and an **Antigravity only** option.
- Lets exported conversations with missing or ambiguous workspaces use a folder you choose.

**Continuing an imported chat starts a new session with imported text as context.** This does not
restore Antigravity's original native session, tool state, or full agent memory. Tools, reasoning,
and attachment contents are not imported into the T3 conversation. Keep your original history.
Signing in to the Antigravity CLI does not necessarily authenticate T3's separate ACP connection.
Reading/importing history does not require a successful T3 provider sign-in.

## Compatibility

| Component       | Validated target                                                                                               |
| --------------- | -------------------------------------------------------------------------------------------------------------- |
| T3 source       | [`49a9e80e`](https://github.com/pingdotgg/t3code/tree/49a9e80e0b30e3012412bcc564bb5e52e09d1c1d), version 0.1.3 |
| Packaging       | Windows x64, matching per-user T3 installation                                                                 |
| Build runtime   | Node.js **26.12.1**, required by that T3 revision                                                              |
| Companion tools | Python 3.11+, Git, PowerShell                                                                                  |
| History         | SQLite steps in format 0; JSON trajectories from the local Antigravity service                                 |

The local service's trajectory API is undocumented and may change. Older encrypted `.pb` files
require that service; this project does not decrypt them itself. macOS, Linux, ARM64, and other
T3 revisions are untested. The installer refuses mismatched versions or changed bundle hashes.

## Quick start on Windows

Run these commands from this repository in PowerShell. Paths below are examples relative to it.
Keep private exports and build output **outside** the repository.

### 1. Prepare and build T3

Install Git, Python 3.11+, and Node.js 26.12.1 first. You also need the matching T3 0.1.3 installation;
do not downgrade an existing installation or its database just to use this patch.

```powershell
python scripts/prepare_checkout.py --destination ..\t3code-import
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Build-Windows.ps1 -Checkout ..\t3code-import
```

The first command fetches only the pinned revision and applies `patches/antigravity-import.patch`.
The second installs upstream dependencies, runs affected typechecks and the focused import tests,
then builds the server and web client. It copies upstream's `.env.example` if `.env` is absent so
T3 Connect's public production configuration remains enabled. No server-side secrets are needed.

### 2. Export and prepare your history

Open Antigravity, then run:

```powershell
python tools/export.py --output ..\private-agy-export
node tools/prepare.mjs --checkout ..\t3code-import --input ..\private-agy-export --output ..\private-agy-prepared --fallback "$HOME\Antigravity Imported Chats"
```

The exporter discovers standard `.gemini` stores and talks only to `127.0.0.1`. On Windows it reads
the local language server's token in memory; it does not print or save the token. If several
servers are running, select the intended one with `--pid <process-id>`. Do not run the internal
`Find-Antigravity.ps1` helper directly: its captured output includes the local service token.

If a local service export fails, `export.py` exits with status 1 and writes a private report.
You can still run `prepare.mjs`, which falls back to read-only SQLite. Use `export.py --offline`
to inventory SQLite history without contacting the service. Encrypted conversations that remain
unreadable are reported as failures, not silently imported as empty chats. Preparation also exits
with status 1 if anything failed. Review the reports locally; the installer rejects partial preparation.

The preparation tool does not recover native conversation titles from summary databases. T3 uses
the first user message as a fallback title. Original workspace paths remain in private export metadata.
Use a fresh output folder for each run; these tools do not overwrite previous exports.

### 3. Package and check the update

```powershell
node scripts/package-windows.mjs --checkout ..\t3code-import --output ..\private-t3-bundle
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Install-Windows.ps1 -Bundle ..\private-t3-bundle -Exports ..\private-agy-prepared -VerifyOnly
```

Packaging reuses your installed runtime dependencies and replaces the server/client build in a
new archive. It verifies that native dependencies remain byte-identical. It does not change your
installation. For a non-default installation, supply `--resources <installation>\resources` when
packaging and `-InstallDirectory <installation>` when installing.

### 4. Install and import

Quit T3 completely, including its tray icon. Then run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Install-Windows.ps1 -Bundle ..\private-t3-bundle -Exports ..\private-agy-prepared
```

The installer saves the original server archive, stages prepared exports, and applies the new
bundle. It never kills processes or edits/replaces your chat database. Use `-T3Home <path>` if your
T3 data directory differs from the default.

Open T3 normally, enable Antigravity under Providers, and choose **Settings → General → Import history**.
Continue to the import step, enable **Import Antigravity history only** and **Include older
conversations and full text history**, select the projects, then import.

## Rollback

Quit T3, then restore the bundle using the same manifest:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Install-Windows.ps1 -Bundle ..\private-t3-bundle -Restore
```

This restores application code; it does not delete imported chats or prepared exports. An official
T3 update can replace this custom bundle. Do not reapply it over a newer release: port and test the
patch against that version first. Keep the private bundle directory until you no longer need rollback.

## Limits and troubleshooting

- Start with a full-history import. Switching from a previously completed partial import to full
  history does not upgrade that existing import automatically.
- Full history raises the per-attempt file limit to 5,000, but byte and input-record budgets still
  apply. Check the UI's skipped count and private preparation report rather than assuming all chats imported.
- A staged JSON export takes precedence over the SQLite conversation with the same ID. It is a
  snapshot, not a live sync; later messages in Antigravity are not automatically imported.
- Missing chats may have unsupported encodings, encrypted history unavailable to the local service,
  or unusable workspace paths. Preparation records failures and assigns a fallback workspace when needed.
- The updater refuses a running installation. Close T3 instead of terminating arbitrary processes.
- Real provider continuation and Google sign-in are separate from history import and have not been
  validated by the companion test suite.

## Development and privacy

```powershell
python -m unittest discover -s tests -v
node --test tests/paths.test.mjs tests/package.test.mjs
git add README.md LICENSE NOTICE SECURITY.md CONTRIBUTING.md UPSTREAM_REVISION .gitignore .gitattributes patches tools scripts tests .github
python scripts/verify-public.py
```

The companion tests use generated synthetic histories and a loopback HTTP fixture. The patch also
contains focused T3 parser/scanner/importer tests. An optional GitHub Actions template checks the
public file index and patch applicability without exporting real history, invoking real agents,
or uploading test artifacts. To enable it, copy `.github/verify-workflow.example.yml` to
`.github/workflows/verify.yml` using GitHub credentials with permission to edit Actions workflows.
Automatic CI is not enabled in this repository; the template is provided for maintainers and forks.

To include the SQLite preparation and package integration tests, set
`T3_IMPORT_TEST_CHECKOUT` to the absolute path of a patched T3 checkout with dependencies
installed, then run the test commands again. Without it, those integration tests are explicitly skipped.
Installer tests use a disposable synthetic installation and run only on Windows.

Read [SECURITY.md](SECURITY.md) before sharing diagnostics and [CONTRIBUTING.md](CONTRIBUTING.md)
before updating the patch. Pattern scans are a guardrail, not proof that arbitrary data is safe to publish.

## Attribution

Built on [T3 Code](https://github.com/pingdotgg/t3code), licensed under MIT. The approach was informed
by the [agy-reader](https://github.com/mjacobs/agy-reader) storage/API documentation; no code from that
project is vendored here. See [NOTICE](NOTICE) and [LICENSE](LICENSE).

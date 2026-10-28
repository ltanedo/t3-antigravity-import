param([Parameter(Mandatory)][string]$Checkout)
$ErrorActionPreference = 'Stop'
$Checkout = (Resolve-Path -LiteralPath $Checkout).Path
$revision = (Get-Content -LiteralPath (Join-Path $PSScriptRoot '..\UPSTREAM_REVISION') -Raw).Trim()
if ((git -C $Checkout rev-parse HEAD).Trim() -ne $revision) { throw 'Checkout is not the pinned revision.' }
if ((node --version).Trim() -ne 'v26.12.1') { throw 'Install Node.js 26.12.1, as required by the pinned upstream revision.' }
Push-Location -LiteralPath $Checkout
try {
    # These are public production identifiers supplied by upstream, not secrets.
    if (-not (Test-Path -LiteralPath '.env')) { Copy-Item -LiteralPath '.env.example' -Destination '.env' }
    & npm.cmd exec --yes --package=vite-plus@1.4.0 -- vp install
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
    & .\node_modules\.bin\vp.cmd run --filter t3 --filter '@t3tools/web' typecheck
    if ($LASTEXITCODE -ne 0) { throw 'Typecheck failed.' }
    & .\node_modules\.bin\vp.cmd test run apps/server/src/project/AntigravityTranscript.test.ts apps/server/src/project/AgentSessionScanner.test.ts apps/server/src/project/AgentSessionImporter.test.ts
    if ($LASTEXITCODE -ne 0) { throw 'Import tests failed.' }
    & .\node_modules\.bin\vp.cmd run --filter t3 build
    if ($LASTEXITCODE -ne 0) { throw 'Build failed.' }
} finally { Pop-Location }

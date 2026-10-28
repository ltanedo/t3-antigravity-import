param(
    [Parameter(Mandatory)][string]$Bundle,
    [string]$Exports,
    [string]$InstallDirectory = (Join-Path $env:LOCALAPPDATA 'Programs\t3code'),
    [string]$T3Home = (Join-Path $env:USERPROFILE '.t3'),
    [switch]$VerifyOnly,
    [switch]$Restore
)
$ErrorActionPreference = 'Stop'
function Get-Sha256([string]$Path) {
    $stream = [IO.File]::OpenRead($Path)
    $sha = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-', '').ToLowerInvariant() }
    finally { $sha.Dispose(); $stream.Dispose() }
}
$Bundle = (Resolve-Path -LiteralPath $Bundle).Path
$InstallDirectory = (Resolve-Path -LiteralPath $InstallDirectory).Path
$resources = Join-Path $InstallDirectory 'resources'
$current = Join-Path $resources 'server.asar'
$manifest = Get-Content -LiteralPath (Join-Path $Bundle 'manifest.json') -Raw | ConvertFrom-Json
if ($manifest.originalSha256 -notmatch '^[0-9a-f]{64}$' -or $manifest.updatedSha256 -notmatch '^[0-9a-f]{64}$') { throw 'Invalid manifest.' }
$backup = Join-Path $resources ('server.asar.before-import-' + $manifest.originalSha256.Substring(0,12))
$candidate = if ($Restore) { $backup } else { Join-Path $Bundle 'server.asar' }
$expected = if ($Restore) { $manifest.originalSha256 } else { $manifest.updatedSha256 }
if ((Get-Sha256 $candidate) -ne $expected) { throw 'Bundle integrity check failed.' }
$currentHash = (Get-Sha256 $current)
if ($currentHash -ne $manifest.originalSha256 -and $currentHash -ne $manifest.updatedSha256) { throw 'Installed T3 changed since packaging. Rebuild against the installed version.' }
$nativeRoot = [IO.Path]::GetFullPath($current + '.unpacked') + [IO.Path]::DirectorySeparatorChar
foreach ($entry in $manifest.nativeHashes.PSObject.Properties) {
    $file = [IO.Path]::GetFullPath((Join-Path $nativeRoot $entry.Name))
    if (-not $file.StartsWith($nativeRoot, [StringComparison]::OrdinalIgnoreCase)) { throw 'Invalid native dependency path.' }
    if ((Get-Sha256 $file) -ne $entry.Value) { throw 'Installed native dependency changed. Rebuild the bundle.' }
}
$files = @()
if ($Exports -and -not $Restore) {
    $Exports = (Resolve-Path -LiteralPath $Exports).Path
    $report = @(Get-Content -LiteralPath (Join-Path $Exports 'preparation-report.json') -Raw | ConvertFrom-Json)
    if (@($report | Where-Object { $null -ne $_.error }).Count -gt 0) { throw 'Some conversations failed preparation. Review the private report before installing.' }
    $files = @(Get-ChildItem -LiteralPath $Exports -Filter '*.trajectory.json' -File)
    if ($files.Count -ne $report.Count) { throw 'Prepared export count does not match its report.' }
}
if ($VerifyOnly) { Write-Output 'Bundle, installed dependencies, and requested exports verified. Nothing changed.'; return }
$running = @(Get-Process -ErrorAction SilentlyContinue | Where-Object {
    $_.Path -and (Split-Path -Parent $_.Path) -eq $InstallDirectory
})
if ($running.Count) { throw 'Quit T3 completely, including its tray icon, before applying or restoring. No processes will be stopped automatically.' }
if ($files.Count) {
    $destination = Join-Path $T3Home 'userdata\imports\antigravity'
    New-Item -ItemType Directory -Force -Path $destination | Out-Null
    foreach ($file in $files) {
        if ($file.Name -notmatch '^[0-9a-f-]{36}\.trajectory\.json$') { throw 'Invalid export filename.' }
        $target = Join-Path $destination $file.Name
        if (Test-Path -LiteralPath $target) {
            if ((Get-Sha256 $target) -ne (Get-Sha256 $file.FullName)) { throw 'A different export already exists in the import folder.' }
        } else { Copy-Item -LiteralPath $file.FullName -Destination $target }
    }
}
if ($currentHash -eq $expected) { Write-Output 'Requested bundle is already installed.'; return }
if (-not $Restore) {
    if (Test-Path -LiteralPath $backup) {
        if ((Get-Sha256 $backup) -ne $manifest.originalSha256) { throw 'Existing backup does not match the original.' }
    } else { Copy-Item -LiteralPath $current -Destination $backup }
}
$recovery = if ($Restore) { Join-Path $Bundle 'server.asar' } else { $backup }
try {
    # Keep the existing file's access permissions. T3 must be closed during this copy.
    [IO.File]::Copy($candidate, $current, $true)
    if ((Get-Sha256 $current) -ne $expected) { throw 'Installed bundle verification failed.' }
} catch {
    [IO.File]::Copy($recovery, $current, $true)
    throw
}
Write-Output 'Bundle applied. Open T3 normally. No chat database was edited or replaced.'
if (-not $Restore) { Write-Output 'Settings > General > Import history: enable Antigravity only and full text history, select projects, and import.' }

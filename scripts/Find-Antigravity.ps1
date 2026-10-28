param([int]$ProcessId = 0)
$ErrorActionPreference = 'Stop'
# Output contains a local service token. The Python exporter captures it in memory.
# Do not run this helper directly or attach its output to issues.
$matches = @(Get-CimInstance Win32_Process -Filter "Name = 'language_server.exe'" | Where-Object {
    if ($ProcessId) { $_.ProcessId -eq $ProcessId }
    else { $_.CommandLine -match '--standalone(?:\s|$)' }
})
if ($matches.Count -ne 1) { throw 'Cannot choose one Antigravity server. Start Antigravity or select its process with --pid.' }
$server = $matches[0]
$tokenMatch = [regex]::Match($server.CommandLine, '--csrf_token(?:=|\s+)([^\s]+)')
if (-not $tokenMatch.Success) { throw 'Local Antigravity service token was not found.' }
$ports = @(Get-NetTCPConnection -State Listen -OwningProcess $server.ProcessId | Select-Object -ExpandProperty LocalPort -Unique)
@{ ports = $ports; token = $tokenMatch.Groups[1].Value.Trim('"') } | ConvertTo-Json -Compress

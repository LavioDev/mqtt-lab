# Docker-only launcher for PowerShell: the host needs nothing but Docker Desktop.
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
# C:\a\b -> /c/a/b so the Docker daemon resolves bind mounts from nested compose calls.
$p = (Get-Location).Path.Replace('\', '/')
$env:HOST_PROJECT_DIR = if ($p -match '^([A-Za-z]):(.*)$') { '/' + $Matches[1].ToLower() + $Matches[2] } else { $p }

$c = @('compose', '-f', 'compose.tools.yaml')
if ($args.Count -gt 0 -and $args[0] -eq 'firmware') {
    if ($args.Count -gt 1 -and $args[1] -eq 'flash') { docker @c --profile flash run --rm flash }
    else { New-Item -ItemType Directory -Force firmware/build | Out-Null; docker @c run --rm firmware }
} else {
    docker @c run --rm tools scripts/lab.py @args
}
exit $LASTEXITCODE

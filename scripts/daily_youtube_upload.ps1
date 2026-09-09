# Runs once a day via Windows Task Scheduler (registered by
# scripts\register_youtube_task.ps1) — uploads a small, steady drip of
# lessons to YouTube rather than dumping the whole eligible batch at
# once. See apps.catalog.management.commands.attach_to_youtube's own
# docstring for the full upload logic and the real reasoning behind
# --limit here (content-strategy pacing, not the API's quota ceiling —
# the quota alone would allow up to 6/day).
#
# Reads secrets from .env.youtube-task (gitignored, never touched by
# any Claude session — see .env.youtube-task.example for the template)
# rather than hardcoding them here, so this script itself is safe to
# read, edit, or eventually commit without exposing anything.

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$secretsFile = Join-Path $repoRoot ".env.youtube-task"
if (-not (Test-Path $secretsFile)) {
    Write-Error "Missing $secretsFile — copy .env.youtube-task.example to .env.youtube-task and fill in the real values first."
    exit 1
}

Get-Content $secretsFile | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -match '^\s*$') { return }
    $parts = $_ -split '=', 2
    if ($parts.Length -eq 2) {
        [System.Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), "Process")
    }
}
$env:DJANGO_SETTINGS_MODULE = "config.settings.prod"

$logDir = Join-Path $repoRoot "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$logFile = Join-Path $logDir "youtube-upload.log"

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
"=== $timestamp ===" | Out-File -Append -Encoding utf8 $logFile

& "$repoRoot\venv\Scripts\python.exe" manage.py attach_to_youtube --limit=1 2>&1 |
    Tee-Object -Append -FilePath $logFile

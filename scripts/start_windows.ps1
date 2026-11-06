# Start FinAlly in Docker. Usage: .\start_windows.ps1 [-Build] [-Open]
param([switch]$Build, [switch]$Open)
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
$Name = "finally"; $Image = "finally"; $Url = "http://localhost:8000"

docker image inspect $Image *> $null
$exists = ($LASTEXITCODE -eq 0)
if ($Build -or -not $exists) { docker build -t $Image . }
docker rm -f $Name *> $null
$envArgs = @()
if (Test-Path ".env") { $envArgs = @("--env-file", ".env") }
docker run -d --name $Name -p 8000:8000 -v finally-data:/app/db @envArgs $Image | Out-Null
Write-Host "FinAlly running at $Url"
if ($Open) { Start-Process $Url }

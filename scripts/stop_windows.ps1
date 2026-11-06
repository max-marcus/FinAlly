# Stop and remove the FinAlly container. The data volume is kept.
docker rm -f finally *> $null
Write-Host "FinAlly stopped (volume finally-data preserved)."

$ErrorActionPreference = "Stop"

$backupRoot = "C:\ESRM-Backups"
$dailyFolder = Join-Path $backupRoot "Daily"
$logFolder = Join-Path $backupRoot "Logs"
$keyFile = "C:\ESRM-Backup-Keys\esrm_backup_ed25519"
$knownHostsFile = "C:\ESRM-Backup-Keys\known_hosts"
$sftpExe = "C:\Windows\System32\OpenSSH\sftp.exe"
$server = "frappe@160.30.47.12"
$port = 22

New-Item -ItemType Directory -Path $dailyFolder -Force | Out-Null
New-Item -ItemType Directory -Path $logFolder -Force | Out-Null

$logFile = Join-Path $logFolder ("backup-{0}.log" -f (Get-Date -Format "yyyyMMdd"))
$batchFile = Join-Path $env:TEMP ("esrm-sftp-{0}.txt" -f [guid]::NewGuid())

try {
    @"
lcd $dailyFolder
mget *
bye
"@ | Set-Content -LiteralPath $batchFile -Encoding ascii

    $arguments = @(
        "-b", $batchFile,
        "-i", $keyFile,
        "-P", "$port",
        "-o", "BatchMode=yes",
        "-o", "StrictHostKeyChecking=yes",
        "-o", "UserKnownHostsFile=$knownHostsFile",
        $server
    )

    $output = & $sftpExe @arguments 2>&1
    $output | Add-Content -LiteralPath $logFile
    if ($LASTEXITCODE -ne 0) {
        throw "SFTP download failed with exit code $LASTEXITCODE."
    }

    $checksumFile = Join-Path $dailyFolder "SHA256SUMS"
    if (-not (Test-Path -LiteralPath $checksumFile)) {
        throw "SHA256SUMS was not downloaded."
    }

    foreach ($line in Get-Content -LiteralPath $checksumFile) {
        if ($line -notmatch "^([a-fA-F0-9]{64})\s+\*?(.+)$") {
            continue
        }
        $expectedHash = $matches[1].ToUpperInvariant()
        $fileName = $matches[2]
        $filePath = Join-Path $dailyFolder $fileName
        if (-not (Test-Path -LiteralPath $filePath)) {
            throw "Expected backup file is missing: $fileName"
        }
        $actualHash = (Get-FileHash -LiteralPath $filePath -Algorithm SHA256).Hash
        if ($actualHash -ne $expectedHash) {
            throw "Checksum mismatch: $fileName"
        }
    }

    $latestDatabase = Get-ChildItem -LiteralPath $dailyFolder -File |
        Where-Object { $_.Name -like "*database.sql.gz" } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if (-not $latestDatabase -or $latestDatabase.Length -lt 1024) {
        throw "No valid database backup was downloaded."
    }

    $cutoff = (Get-Date).AddDays(-90)
    Get-ChildItem -LiteralPath $dailyFolder -File |
        Where-Object {
            $_.LastWriteTime -lt $cutoff -and
            $_.Name -ne "SHA256SUMS"
        } |
        Remove-Item -Force

    "SUCCESS $(Get-Date -Format o) $($latestDatabase.Name)" |
        Add-Content -LiteralPath $logFile
}
catch {
    "FAILED $(Get-Date -Format o) $($_.Exception.Message)" |
        Add-Content -LiteralPath $logFile
    throw
}
finally {
    if (Test-Path -LiteralPath $batchFile) {
        Remove-Item -LiteralPath $batchFile -Force
    }
}

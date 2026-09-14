# backup_before_build.ps1
# Windows PowerShell 5.1 compatible - ASCII only
# Creates a timestamped full backup of the project directory (including db,
# ignored/untracked files, dist, etc.) using robocopy, saves git status/diff,
# and a git bundle with the full committed history.

$ErrorActionPreference = 'Stop'

try {
    $ScriptDir = Split-Path -Parent -Path $MyInvocation.MyCommand.Path

    Write-Host "==================================================="
    Write-Host "  Backup before build - Project: $ScriptDir"
    Write-Host "==================================================="
    Write-Host ""
    Write-Host "IMPORTANT: Please CLOSE the application (and any program"
    Write-Host "using the SQLite database) before continuing."
    Write-Host "NOTE: This is a file copy backup - it does NOT guarantee a"
    Write-Host "live/consistent SQLite backup if the app is still running."
    Write-Host ""
    $answer = Read-Host "Have you closed the application? Type Y to continue"
    if ($answer -notmatch '^[Yy]$') {
        Write-Host "Cancelled by user."
        exit 1
    }

    # --- Validate git repository ---
    $gitRoot = & git -C $ScriptDir rev-parse --show-toplevel 2>$null
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($gitRoot)) {
        Write-Host "ERROR: This directory is not a git repository." -ForegroundColor Red
        exit 1
    }
    $gitRoot = (Resolve-Path $gitRoot).Path
    $scriptNorm = (Resolve-Path $ScriptDir).Path
    if ($gitRoot -ne $scriptNorm) {
        Write-Host "ERROR: Git root ($gitRoot) does not match script directory ($scriptNorm)." -ForegroundColor Red
        exit 1
    }

    # --- Check for at least one commit (bundle fails otherwise) ---
    & git -C $gitRoot rev-parse --verify HEAD 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Git repository has no commits yet; git bundle would fail." -ForegroundColor Red
        Write-Host "Please make an initial commit first, then run this script again."
        exit 1
    }

    # --- Destination ---
    $parent = Split-Path -Parent -Path $ScriptDir
    $projName = Split-Path -Leaf -Path $ScriptDir
    $stamp = Get-Date -Format 'yyyy-MM-dd_HH-mm-ss'
    $dest = Join-Path $parent ("${projName}_backup_$stamp")
    New-Item -ItemType Directory -Path $dest -Force | Out-Null

    # --- robocopy full copy (exclude ONLY source .git) ---
    Write-Host "Copying project to: $dest"
    & robocopy $ScriptDir $dest /E /XD (Join-Path $ScriptDir '.git') /NFL /NDL /NJH /NJS
    $rc = $LASTEXITCODE
    if ($rc -ge 8) {
        Write-Host "ERROR: robocopy failed with exit code $rc. Backup aborted/incomplete." -ForegroundColor Red
        exit $rc
    }
    Write-Host "robocopy completed (code $rc)."

    # --- Save git status and diffs ---
    try {
        & git -C $gitRoot status | Out-File -FilePath (Join-Path $dest 'git_status.txt') -Encoding utf8
        & git -C $gitRoot diff HEAD | Out-File -FilePath (Join-Path $dest 'git_diff_HEAD.txt') -Encoding utf8
        & git -C $gitRoot diff --cached | Out-File -FilePath (Join-Path $dest 'git_diff_cached.txt') -Encoding utf8
    } catch {
        Write-Host "WARNING: could not save git status/diff: $_" -ForegroundColor Yellow
    }

    # --- Git bundle (full committed history and refs) ---
    & git -C $gitRoot bundle create (Join-Path $dest 'repository.bundle') --all
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: git bundle create failed (code $LASTEXITCODE)." -ForegroundColor Red
        exit $LASTEXITCODE
    }

    Write-Host ""
    Write-Host "SUCCESS: Backup created at:" -ForegroundColor Green
    Write-Host "  $dest"
    Write-Host "You can now safely replace main.py and build."
    exit 0
}
catch {
    Write-Host "FATAL ERROR: $_" -ForegroundColor Red
    exit 1
}

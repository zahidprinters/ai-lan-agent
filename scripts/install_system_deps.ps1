param(
    [switch]$SkipVerify
)

$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $root 'scripts\utils.ps1')
$tempRoot = Set-ProjectTempEnvironment -Root $root

Show-ModuleHeader -Title 'AI LAN - SYSTEM DEP INSTALLER' -Task 'Install Windows system binaries for Phase 4 and 4.5' -TempPath $tempRoot

if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    throw 'winget is required for this installer. Install App Installer / winget first and rerun.'
}

$packages = @(
    @{
        Name = 'Tesseract OCR'
        Id = 'UB-Mannheim.TesseractOCR'
        ExpectedPath = 'C:\Program Files\Tesseract-OCR\tesseract.exe'
    },
    @{
        Name = 'Android Platform Tools'
        Id = 'Google.PlatformTools'
        ExpectedPath = Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Packages\Google.PlatformTools_Microsoft.Winget.Source_8wekyb3d8bbwe\platform-tools\adb.exe'
    },
    @{
        Name = 'scrcpy'
        Id = 'Genymobile.scrcpy'
        ExpectedPath = Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Packages\Genymobile.scrcpy_Microsoft.Winget.Source_8wekyb3d8bbwe\scrcpy-win64-v3.3.4\scrcpy.exe'
    }
)

foreach ($package in $packages) {
    Write-Host "[INFO] Installing or upgrading $($package.Name)..." -ForegroundColor Green
    & winget install --id $package.Id -e --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        if (Test-Path $package.ExpectedPath) {
            Write-Host "[WARN] winget returned a nonzero exit code for $($package.Name), but the expected executable already exists. Continuing." -ForegroundColor Yellow
        }
        else {
            throw "Failed to install $($package.Name) via winget."
        }
    }
}

if ($SkipVerify) {
    Write-Host '[INFO] Skipping verification by request.' -ForegroundColor Yellow
    exit 0
}

Write-Host '[INFO] Verifying installed executable paths...' -ForegroundColor Green

foreach ($package in $packages) {
    if (Test-Path $package.ExpectedPath) {
        Write-Host "[OK] $($package.Name): $($package.ExpectedPath)" -ForegroundColor DarkGreen
    }
    else {
        Write-Host "[WARN] Expected path not found for $($package.Name): $($package.ExpectedPath)" -ForegroundColor Yellow
    }
}

Write-Host '[INFO] Verification commands:' -ForegroundColor Cyan

$tesseractPath = $packages[0].ExpectedPath
$adbPath = $packages[1].ExpectedPath
$scrcpyPath = $packages[2].ExpectedPath

if (Test-Path $tesseractPath) {
    & $tesseractPath --version
}

if (Test-Path $adbPath) {
    & $adbPath version
}

if (Test-Path $scrcpyPath) {
    & $scrcpyPath --version
}

Write-Host '[INFO] System dependency setup completed.' -ForegroundColor Green
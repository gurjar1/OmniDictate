param(
    [string]$InstallerPath = "smoke_test_assets\packaging\installer-whisper-user-smoke\OmniDictate_Setup_v3.0.0-whisper-user-smoke.exe",
    [string]$InstallDir = (Join-Path $env:LOCALAPPDATA "OmniDictateSmoke"),
    [int]$LaunchSeconds = 12,
    [switch]$UseInstallerDefaults,
    [switch]$AllowRemoveExisting
)

$ErrorActionPreference = "Stop"

function Resolve-WorkspacePath([string]$PathValue) {
    if ([System.IO.Path]::IsPathRooted($PathValue)) {
        return $PathValue
    }
    return (Join-Path (Get-Location) $PathValue)
}

$installer = Resolve-WorkspacePath $InstallerPath
if (-not (Test-Path -LiteralPath $installer)) {
    throw "Installer not found: $installer"
}

if ((Test-Path -LiteralPath $InstallDir) -and -not $AllowRemoveExisting) {
    throw "Install directory already exists. Refusing to remove without -AllowRemoveExisting: $InstallDir"
}

if (Test-Path -LiteralPath $InstallDir) {
    Remove-Item -LiteralPath $InstallDir -Recurse -Force
}

$artifactDir = Split-Path -Parent $installer
$installLog = Join-Path $artifactDir "install-smoke.log"
$uninstallLog = Join-Path $artifactDir "uninstall-smoke.log"
Remove-Item -LiteralPath $installLog, $uninstallLog -Force -ErrorAction SilentlyContinue

Write-Host "Installing to $InstallDir"
$installArgs = @(
    "/VERYSILENT",
    "/SUPPRESSMSGBOXES",
    "/NORESTART"
)
if (-not $UseInstallerDefaults) {
    $installArgs += "/CURRENTUSER"
    $installArgs += "/DIR=`"$InstallDir`""
}
$installArgs += "/MERGETASKS=!desktopicon"
$installArgs += "/LOG=`"$installLog`""
$installProcess = Start-Process -FilePath $installer -ArgumentList ($installArgs -join " ") -Wait -PassThru
if ($installProcess.ExitCode -ne 0) {
    throw "Installer exited with $($installProcess.ExitCode)"
}

$installedExe = Join-Path $InstallDir "OmniDictate.exe"
if (-not (Test-Path -LiteralPath $installedExe)) {
    throw "Installed executable not found: $installedExe"
}
$pythonDll = Join-Path $InstallDir "_internal\python311.dll"
if (-not (Test-Path -LiteralPath $pythonDll)) {
    throw "Installed Python DLL not found: $pythonDll"
}
if ((Select-String -LiteralPath $installLog -Pattern "build-whisper-final" -Quiet -ErrorAction SilentlyContinue)) {
    throw "Install log references build-whisper-final; Inno SourceDir may point at the PyInstaller work directory."
}

Write-Host "Launching installed executable"
$appProcess = Start-Process -FilePath $installedExe -PassThru
$deadline = (Get-Date).AddSeconds($LaunchSeconds)
do {
    Start-Sleep -Milliseconds 250
    $currentProcess = Get-Process -Id $appProcess.Id -ErrorAction SilentlyContinue
    if (-not $currentProcess) {
        throw "Installed executable exited during launch smoke with code $($appProcess.ExitCode)"
    }
    if ($currentProcess.MainWindowHandle -ne 0) {
        break
    }
} while ((Get-Date) -lt $deadline)

$currentProcess = Get-Process -Id $appProcess.Id -ErrorAction SilentlyContinue
if (-not $currentProcess) {
    throw "Installed executable exited during launch smoke with code $($appProcess.ExitCode)"
}
if ($currentProcess.MainWindowHandle -eq 0) {
    Stop-Process -Id $appProcess.Id -Force -ErrorAction SilentlyContinue
    throw "Installed executable did not open a main window within $LaunchSeconds seconds."
}
if (-not $currentProcess.Responding) {
    Stop-Process -Id $appProcess.Id -Force -ErrorAction SilentlyContinue
    throw "Installed executable opened a window but is not responding."
}
Stop-Process -Id $appProcess.Id -Force

Start-Sleep -Seconds 2
$uninstaller = Join-Path $InstallDir "unins000.exe"
if (-not (Test-Path -LiteralPath $uninstaller)) {
    throw "Uninstaller not found: $uninstaller"
}

Write-Host "Uninstalling"
$uninstallArgs = @(
    "/VERYSILENT",
    "/SUPPRESSMSGBOXES",
    "/NORESTART",
    "/LOG=`"$uninstallLog`""
)
$uninstallProcess = Start-Process -FilePath $uninstaller -ArgumentList ($uninstallArgs -join " ") -Wait -PassThru
if ($uninstallProcess.ExitCode -ne 0) {
    throw "Uninstaller exited with $($uninstallProcess.ExitCode)"
}

Start-Sleep -Seconds 2
if (Test-Path -LiteralPath $installedExe) {
    throw "Installed executable still exists after uninstall: $installedExe"
}
if (Test-Path -LiteralPath (Join-Path $InstallDir "_internal")) {
    throw "Installed _internal directory still exists after uninstall."
}
if (Test-Path -LiteralPath $InstallDir) {
    $remaining = Get-ChildItem -LiteralPath $InstallDir -Force -ErrorAction SilentlyContinue
    if ($remaining) {
        throw "Install directory still has remaining files after uninstall: $InstallDir"
    }
}

Write-Host "Installer smoke passed."
Write-Host "Install log: $installLog"
Write-Host "Uninstall log: $uninstallLog"

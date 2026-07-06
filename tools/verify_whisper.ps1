param(
    [string]$Model = "tiny",
    [string]$Expected = "hello world this is a simple speech test",
    [double]$MinWordRatio = 0.75
)

$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$venvPython = Join-Path $repoRoot "venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $python = $venvPython
} else {
    $python = "python"
}

Set-Location $repoRoot
& $python tools\whisper_fixture_test.py --model $Model --expected $Expected --min-word-ratio $MinWordRatio
if ($LASTEXITCODE -ne 0) {
    throw "Whisper fixture gate failed."
}

Write-Host "Whisper fixture gate passed."

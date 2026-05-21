param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

& $Python -m pip install --upgrade pip
& $Python -m pip install -e . pyinstaller

& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name Replibook `
    --icon replibook/assets/replibook-icon.ico `
    --add-data "replibook/assets;replibook/assets" `
    --add-data "replibook/generator/templates;replibook/generator/templates" `
    replibook/gui/app.py

if (!(Test-Path "dist/Replibook.exe")) {
    throw "Build failed: dist/Replibook.exe was not created"
}

Write-Host "Built dist/Replibook.exe"

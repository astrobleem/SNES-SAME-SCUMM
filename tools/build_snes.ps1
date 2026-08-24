param(
    [string]$PoppyRoot = "E:\gh\poppy-astrobleem",
    [string]$DotnetExe = "$env:USERPROFILE\.dotnet\dotnet.exe",
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$PoppyDll = Join-Path $PoppyRoot "src\Poppy.CLI\bin\Release\net10.0\poppy.dll"
$ExpectedPoppySha256 = "715b14431478b62433498cc516c1cbbb8f418c1d7b39a8e71098ed98d9c9167e"
$env:PYTHONPATH = Join-Path $Root "src"

Push-Location $Root
try {
    & $PythonExe "tools\check_poppy.py" $PoppyRoot --dll $PoppyDll
    if ($LASTEXITCODE -ne 0) { throw "Poppy identity check failed" }
    $PoppyHash = (Get-FileHash $PoppyDll -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($PoppyHash -ne $ExpectedPoppySha256) {
        throw "Refusing unpinned Poppy DLL: observed $PoppyHash; expected $ExpectedPoppySha256"
    }
    Write-Host "Poppy SHA-256: $PoppyHash"

    & $PythonExe -m same.cli abi generate "runtime\snes\generated\abi.inc.pasm"
    if ($LASTEXITCODE -ne 0) { throw "ABI generation failed" }

    & $PythonExe "tools\lint_poppy.py" "runtime\snes\main.pasm"
    if ($LASTEXITCODE -ne 0) { throw "Poppy static checks failed" }

    New-Item -ItemType Directory -Force -Path "build" | Out-Null
    & $DotnetExe $PoppyDll -t snes -I "runtime\snes" "runtime\snes\main.pasm" -o "build\same-engine-host.sfc" --no-verify
    if ($LASTEXITCODE -ne 0) { throw "Poppy assembly failed" }

    & $PythonExe "tools\finalize_snes_rom.py" "build\same-engine-host.sfc"
    if ($LASTEXITCODE -ne 0) { throw "SNES ROM finalization failed" }

    & $PythonExe "tools\audit_snes_rom.py" "build\same-engine-host.sfc"
    if ($LASTEXITCODE -ne 0) { throw "SNES ROM audit failed" }

    $Hash = (Get-FileHash "build\same-engine-host.sfc" -Algorithm SHA256).Hash.ToLowerInvariant()
    Write-Host "ROM: build\same-engine-host.sfc"
    Write-Host "SHA-256: $Hash"
}
finally {
    Pop-Location
}

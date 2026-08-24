param([string]$PythonExe = "python")

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$env:PYTHONPATH = Join-Path $Root "src"

Push-Location $Root
try {
    & $PythonExe "tools\generate_engine_fixtures.py"
    if ($LASTEXITCODE -ne 0) { throw "Fixture generation failed" }

    & $PythonExe -m same.cli abi generate "runtime\snes\generated\abi.inc.pasm"
    if ($LASTEXITCODE -ne 0) { throw "ABI generation failed" }

    & $PythonExe -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) { throw "Unit tests failed" }

    & $PythonExe "tools\lint_poppy.py" "runtime\snes\main.pasm"
    if ($LASTEXITCODE -ne 0) { throw "Poppy source lint failed" }

    Get-ChildItem "examples\targets\*.json" | ForEach-Object {
        & $PythonExe -m same.cli target validate $_.FullName | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Target validation failed: $($_.FullName)" }
    }

    Get-ChildItem "examples\profiles\*.json" | ForEach-Object {
        & $PythonExe -m same.cli engine validate $_.FullName | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Engine profile validation failed: $($_.FullName)" }
    }

    New-Item -ItemType Directory -Force -Path "out" | Out-Null
    & $PythonExe -m same.cli package build `
        "examples\packages\demo-package.json" "out\demo.samepkg" `
        --poppy-include "out\demo-package.inc.pasm"
    if ($LASTEXITCODE -ne 0) { throw "Machine package demo failed" }

    & $PythonExe -m same.cli package build `
        "examples\packages\adventure-demo-package.json" "out\adventure-demo.samepkg" `
        --poppy-include "out\adventure-demo.inc.pasm"
    if ($LASTEXITCODE -ne 0) { throw "Adventure package demo failed" }

    & $PythonExe -m same.cli engine run `
        "examples\profiles\scumm_v5_conformance.json" --frames 120 `
        --output "out\scumm-v5-report.json" `
        --framebuffer "out\scumm-v5-frame.png" `
        --save-file "out\scumm-v5-slot0.same-save"
    if ($LASTEXITCODE -ne 0) { throw "SCUMM v5 engine demo failed" }

    & $PythonExe -m same.cli engine run `
        "examples\profiles\agi_v2_conformance.json" --frames 120 `
        --output "out\agi-v2-report.json" `
        --framebuffer "out\agi-v2-frame.png" `
        --save-file "out\agi-v2-slot0.same-save"
    if ($LASTEXITCODE -ne 0) { throw "AGI v2 engine demo failed" }

    & $PythonExe -m same.cli simulate "examples\targets\genesis.json" `
        --frames 120 --input-script "examples\input\genesis-demo.json" `
        --output "out\genesis-simulation.json"
    if ($LASTEXITCODE -ne 0) { throw "Legacy machine simulation failed" }

    & $PythonExe -m same.cli audio demo `
        --trace "examples\audio\sn76489-demo.jsonl" `
        --wav "out\sn76489-demo.wav" --duration 1.25
    if ($LASTEXITCODE -ne 0) { throw "Audio demo failed" }

    Push-Location "labs\vdp"
    try {
        & $PythonExe -m same_vdp.cli verify --root .
        if ($LASTEXITCODE -ne 0) { throw "SAME-VDP verification failed" }
    }
    finally {
        Pop-Location
    }

    Write-Host "SAME validation: PASS"
}
finally {
    Pop-Location
}

param(
    [string]$PoppyRoot = "E:\gh\poppy-astrobleem",
    [string]$DotnetExe = "$env:USERPROFILE\.dotnet\dotnet.exe",
    [string]$PythonExe = "python",
    [string]$TadCompiler = "tad-compiler"
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$PoppyDll = Join-Path $PoppyRoot "src\Poppy.CLI\bin\Release\net10.0\poppy.dll"
$MusicCatalog = if ($env:SAME_MUSIC_CATALOG) {
    $env:SAME_MUSIC_CATALOG
} else {
    Join-Path $Root "examples\resources\music\fate_s6_compiled.json"
}
$env:PYTHONPATH = Join-Path $Root "src"
$Carrier = if ($env:SAME_SNES_CARRIER) { $env:SAME_SNES_CARRIER } else { "lorom" }
if ($Carrier -notin @("lorom", "sa1_bwram")) {
    throw "Unsupported SAME_SNES_CARRIER: $Carrier"
}
$VideoBackend = if ($env:SAME_SNES_VIDEO_BACKEND) { $env:SAME_SNES_VIDEO_BACKEND } else { "legacy_backdrop" }
if ($VideoBackend -notin @("legacy_backdrop", "mode3_surface")) {
    throw "Unsupported SAME_SNES_VIDEO_BACKEND: $VideoBackend"
}
if ($VideoBackend -eq "mode3_surface" -and $Carrier -ne "sa1_bwram") {
    throw "mode3_surface requires SAME_SNES_CARRIER=sa1_bwram"
}
$Output = if ($env:SAME_SNES_OUTPUT) { $env:SAME_SNES_OUTPUT } else { "build\same-engine-host.sfc" }
$CarrierManifest = [System.IO.Path]::ChangeExtension($Output, "carrier.json")
$VideoBackendManifest = [System.IO.Path]::ChangeExtension($Output, "video-backend.json")

Push-Location $Root
try {
    & $PythonExe "tools\check_poppy.py" $PoppyRoot --dll $PoppyDll
    if ($LASTEXITCODE -ne 0) { throw "Poppy identity check failed" }
    $PoppyHash = (Get-FileHash $PoppyDll -Algorithm SHA256).Hash.ToLowerInvariant()
    Write-Host "Poppy SHA-256: $PoppyHash"

    & $PythonExe -m same.cli abi generate "runtime\snes\generated\abi.inc.pasm"
    if ($LASTEXITCODE -ne 0) { throw "ABI generation failed" }

    $CarrierArgs = @(
        "tools\generate_snes_carrier.py",
        "--carrier", $Carrier,
        "--rom-size-code", $(if ($Carrier -eq "sa1_bwram" -or $env:SAME_BUILD_SCUMM_M23A -eq "1") { "0x09" } else { "0x07" }),
        "--manifest", $CarrierManifest
    )
    if ($env:SAME_BUILD_SCUMM_M20 -eq "1") { $CarrierArgs += "--save-enabled" }
    & $PythonExe @CarrierArgs
    if ($LASTEXITCODE -ne 0) { throw "SNES carrier generation failed" }
    & $PythonExe "tools\generate_snes_video_backend.py" --backend $VideoBackend --carrier $Carrier --manifest $VideoBackendManifest
    if ($LASTEXITCODE -ne 0) { throw "SNES video-backend generation failed" }

    New-Item -ItemType Directory -Force -Path "build\fate-audio" | Out-Null
    if ($env:SAME_TAD_PREBUILT_DIR) {
        $Prebuilt = (Resolve-Path $env:SAME_TAD_PREBUILT_DIR).Path
        $PrebuiltBin = Join-Path $Prebuilt "tad.bin"
        $PrebuiltInc = Join-Path $Prebuilt "tad.inc"
        if (-not (Test-Path $PrebuiltBin -PathType Leaf) -or
            -not (Test-Path $PrebuiltInc -PathType Leaf)) {
            throw "Prebuilt TAD directory must contain tad.bin and tad.inc: $Prebuilt"
        }
        Copy-Item $PrebuiltBin "build\fate-audio\fate-tad.bin" -Force
        Copy-Item $PrebuiltInc "build\fate-audio\fate-tad.inc" -Force
        Write-Host "Using prebuilt TAD data: $Prebuilt"
    }
    else {
        & $PythonExe "tools\generate_fate_tad_tone.py" "build\fate-audio\fate-tone.wav"
        if ($LASTEXITCODE -ne 0) { throw "Fate source-wave generation failed" }
        & $PythonExe "tools\build_fate_loop_safe_samples.py"
        if ($LASTEXITCODE -ne 0) { throw "Fate loop-safe sample generation failed" }
        & $TadCompiler asar-export --lorom `
            --output-asm "build\fate-audio\fate-tad.asm" `
            --output-bin "build\fate-audio\fate-tad.bin" `
            --output-inc "build\fate-audio\fate-tad.inc" `
            "audio\fate_s6\fate.terrificaudio"
        if ($LASTEXITCODE -ne 0) { throw "Fate TAD compilation failed" }
    }
    & $PythonExe "tools\generate_fate_tad_layout.py" `
        "build\fate-audio\fate-tad.bin" "build\fate-audio\fate-tad.inc" `
        "audio\fate_s6\fate_tad_layout.inc.pasm"
    if ($LASTEXITCODE -ne 0) { throw "Fate TAD layout generation failed" }
    & $PythonExe "tools\generate_music_catalog.py" `
        $MusicCatalog "build\fate-audio\fate-tad.inc" `
        "runtime\snes\generated\music_catalog.inc.pasm" `
        --lifecycle-output "runtime\snes\generated\music_lifecycle_catalog.inc.pasm"
    if ($LASTEXITCODE -ne 0) { throw "Compiled music catalog generation failed" }

    & $PythonExe "tools\lint_poppy.py" "runtime\snes\main.pasm"
    if ($LASTEXITCODE -ne 0) { throw "Poppy static checks failed" }

    New-Item -ItemType Directory -Force -Path "build" | Out-Null
    & $DotnetExe $PoppyDll -t snes -I "runtime\snes" "runtime\snes\main.pasm" -o $Output --no-verify
    if ($LASTEXITCODE -ne 0) { throw "Poppy assembly failed" }

    & $PythonExe "tools\finalize_snes_rom.py" $Output --carrier $Carrier --manifest $CarrierManifest
    if ($LASTEXITCODE -ne 0) { throw "SNES ROM finalization failed" }

    & $PythonExe "tools\audit_snes_rom.py" $Output --carrier $Carrier --manifest $CarrierManifest
    if ($LASTEXITCODE -ne 0) { throw "SNES ROM audit failed" }

    $Hash = (Get-FileHash $Output -Algorithm SHA256).Hash.ToLowerInvariant()
    Write-Host "ROM: $Output"
    Write-Host "SHA-256: $Hash"
}
finally {
    Pop-Location
}

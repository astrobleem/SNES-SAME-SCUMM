#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
POPPY_ROOT="${POPPY_ROOT:-/home/chad/poppy-astrobleem-latest}"
DOTNET_ROOT="${DOTNET_ROOT:-/home/chad/.dotnet10}"
POPPY_DLL="${POPPY_DLL:-$POPPY_ROOT/src/Poppy.CLI/bin/Release/net10.0/poppy.dll}"
PYTHON="${PYTHON:-python3}"
TAD_COMPILER="${TAD_COMPILER:-$ROOT/../terrific-audio-driver/target/release/tad-compiler}"
SAME_MUSIC_CATALOG="${SAME_MUSIC_CATALOG:-$ROOT/examples/resources/music/fate_s6_compiled.json}"
EXPECTED_POPPY_SHA256=715b14431478b62433498cc516c1cbbb8f418c1d7b39a8e71098ed98d9c9167e

cd "$ROOT"
export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
"$PYTHON" tools/check_poppy.py "$POPPY_ROOT" --dll "$POPPY_DLL"
POPPY_SHA256="$(sha256sum "$POPPY_DLL" | awk '{print $1}')"
if [[ "$POPPY_SHA256" != "$EXPECTED_POPPY_SHA256" ]]; then
    echo "Refusing unpinned Poppy DLL: $POPPY_DLL" >&2
    echo "observed: $POPPY_SHA256" >&2
    echo "expected: $EXPECTED_POPPY_SHA256" >&2
    exit 1
fi
echo "Poppy SHA-256: $POPPY_SHA256"
"$PYTHON" -m same.cli abi generate runtime/snes/generated/abi.inc.pasm
mkdir -p build/fate-audio
if [[ -n "${SAME_TAD_PREBUILT_DIR:-}" ]]; then
    PREBUILT_DIR="$(cd "$SAME_TAD_PREBUILT_DIR" && pwd)"
    if [[ ! -f "$PREBUILT_DIR/tad.bin" || ! -f "$PREBUILT_DIR/tad.inc" ]]; then
        echo "Prebuilt TAD directory must contain tad.bin and tad.inc: $PREBUILT_DIR" >&2
        exit 1
    fi
    cp "$PREBUILT_DIR/tad.bin" build/fate-audio/fate-tad.bin
    cp "$PREBUILT_DIR/tad.inc" build/fate-audio/fate-tad.inc
    cp "$PREBUILT_DIR/tad.asm" build/fate-audio/fate-tad.asm
    echo "Using prebuilt TAD data: $PREBUILT_DIR"
else
    "$PYTHON" tools/generate_fate_tad_tone.py build/fate-audio/fate-tone.wav
    "$PYTHON" tools/build_fate_loop_safe_samples.py
    "$TAD_COMPILER" asar-export --lorom \
        --output-asm build/fate-audio/fate-tad.asm \
        --output-bin build/fate-audio/fate-tad.bin \
        --output-inc build/fate-audio/fate-tad.inc \
        audio/fate_s6/fate.terrificaudio
fi
"$PYTHON" tools/generate_fate_tad_layout.py \
    build/fate-audio/fate-tad.bin build/fate-audio/fate-tad.inc \
    "${SAME_TAD_LAYOUT_OUTPUT:-audio/fate_s6/fate_tad_layout.inc.pasm}" \
    --assembly build/fate-audio/fate-tad.asm
"$PYTHON" tools/generate_music_catalog.py \
    "$SAME_MUSIC_CATALOG" build/fate-audio/fate-tad.inc \
    runtime/snes/generated/music_catalog.inc.pasm \
    --lifecycle-output runtime/snes/generated/music_lifecycle_catalog.inc.pasm \
    $([[ "${SAME_BUILD_SCUMM_PHASE6L_A1D:-0}" == "1" ]] && echo --exclude-compiled-song fate_sound_80_default --exclude-compiled-song fate_sound_80_hook14)
ENGINE_SELECTION_ARGS=(--engine "${SAME_SNES_ENGINE:-demo}")
if [[ "${SAME_BUILD_M24RA:-0}" == "1" ]]; then
    ENGINE_SELECTION_ARGS+=(--m24ra)
fi
if [[ "${SAME_BUILD_M24RB:-0}" == "1" ]]; then
    ENGINE_SELECTION_ARGS+=(--m24rb --m24rb-phase-delay "${SAME_M24RB_PHASE_DELAY:-125}")
fi
if [[ "${SAME_BUILD_SCUMM_M23C_CLASS_CONFORMANCE:-0}" == "1" ]]; then
    ENGINE_SELECTION_ARGS+=(--scumm-m23c-class-conformance)
fi
if [[ "${SAME_BUILD_SCUMM_M25A_VALIDATOR:-0}" == "1" ]]; then
    ENGINE_SELECTION_ARGS+=(--scumm-m25a-validator)
fi
if [[ "${SAME_BUILD_SCUMM_SCENARIO_FIXTURE:-0}" == "1" ]]; then
    ENGINE_SELECTION_ARGS+=(--scumm-scenario-fixture)
fi
if [[ "${SAME_BUILD_SCUMM_M25_MOVEMENT:-0}" == "1" ]]; then
    ENGINE_SELECTION_ARGS+=(--scumm-m25-movement)
fi
if [[ "${SAME_BUILD_SCUMM_PHASE6HB:-0}" == "1" ]]; then
    ENGINE_SELECTION_ARGS+=(--scumm-phase6hb)
fi
if [[ "${SAME_BUILD_SCUMM_ROOM_VISUAL:-0}" == "1" ]]; then
    if [[ "${SAME_SNES_CARRIER:-lorom}" != "sa1_bwram" || "${SAME_SNES_VIDEO_BACKEND:-legacy_backdrop}" != "mode3_surface" ]]; then
        echo "SCUMM room visuals require sa1_bwram + mode3_surface" >&2
        exit 1
    fi
    ENGINE_SELECTION_ARGS+=(--scumm-room-visual)
fi
if [[ "${SAME_BUILD_SCUMM_SAVE_PERSISTENCE_VALIDATOR:-0}" == "1" ]]; then
    ENGINE_SELECTION_ARGS+=(--scumm-save-persistence-validator)
fi
if [[ "${SAME_BUILD_SCUMM_M20:-0}" == "1" ]]; then
    ENGINE_SELECTION_ARGS+=(--scumm-m20)
fi
if [[ "${SAME_BUILD_SCUMM_M21:-0}" == "1" ]]; then
    ENGINE_SELECTION_ARGS+=(--scumm-m21)
fi
if [[ "${SAME_BUILD_SCUMM_M22:-0}" == "1" ]]; then
    ENGINE_SELECTION_ARGS+=(--scumm-m22)
    "$PYTHON" tools/generate_music_sections.py \
        audio/fate_s6/m22_sound80/audit.json \
        runtime/snes/generated/music_sections.inc.pasm
fi
if [[ "${SAME_BUILD_SCUMM_M23A:-0}" == "1" ]]; then
    ENGINE_SELECTION_ARGS+=(--scumm-m23a)
    if [[ "${SAME_BUILD_SCUMM_PHASE6L_A1D:-0}" == "1" ]]; then
        ENGINE_SELECTION_ARGS+=(--scumm-phase6la1d)
    fi
    if [[ "${SAME_BUILD_SCUMM_M23B:-0}" == "1" ]]; then
        ENGINE_SELECTION_ARGS+=(--scumm-m23b)
        if [[ "${SAME_BUILD_SCUMM_M23B_NEGATIVE:-0}" == "1" ]]; then
            ENGINE_SELECTION_ARGS+=(--scumm-m23b-negative)
        fi
        if [[ "${SAME_BUILD_SCUMM_M23C:-0}" == "1" ]]; then
            ENGINE_SELECTION_ARGS+=(--scumm-m23c --scumm-m23c-source-room 49 --scumm-m23c-target-room 63 --scumm-m23c-global-script 151)
            if [[ "${SAME_BUILD_SCUMM_M23C_CLASS_CONTROL:-0}" == "1" ]]; then
                ENGINE_SELECTION_ARGS+=(--scumm-m23c-class-control)
            fi
            if [[ "${SAME_BUILD_SCUMM_M23C_SOUND_CONTROL:-0}" == "1" ]]; then
                ENGINE_SELECTION_ARGS+=(--scumm-m23c-sound-control)
            fi
        fi
    fi
    M23A_SOURCE="${SAME_FATE_DEMO_ARCHIVE:-/home/chad/fatedemo-box.zip}"
    M23A_BUILD="$ROOT/build/m23a-rooms"
    mkdir -p "$M23A_BUILD/authentic" "$M23A_BUILD/lifecycle" "$M23A_BUILD/segments"
    if [[ "${SAME_BUILD_SCUMM_M25A_VALIDATOR:-0}" == "1" ]]; then
        M25A_BUILD="$ROOT/build/m25a-validator/${SAME_M25A_VALIDATOR_CASE:-normal}"
        mkdir -p "$M25A_BUILD" "$M25A_BUILD/segments"
        "$PYTHON" tools/build_m25a_validator_room.py \
            --case "${SAME_M25A_VALIDATOR_CASE:-normal}" --output-dir "$M25A_BUILD"
        ROOM_MANIFESTS=(--manifest "$M25A_BUILD/manifest.json")
        ROOM_BINARY_DIR="$M25A_BUILD/segments"
        if [[ "${SAME_M25A_VALIDATOR_CASE:-}" == "startup42" ]]; then
            # The controlled root starts at the source-backed pre-title room.
            # Room 68's authored script owns the ordinary 68 -> 0 -> 75
            # lifecycle; no profile-side room request is injected here.
            ENGINE_SELECTION_ARGS+=(--scumm-scenario-source-actor-state)
            mkdir -p "$M25A_BUILD/room42"
            "$PYTHON" tools/cook_scumm_v5_rooms.py \
                --archive "$M23A_SOURCE" \
                --profile examples/profiles/templates/fate_of_atlantis_demo.json \
                --rooms 1 42 68 75 82 \
                --executable --output-dir "$M25A_BUILD/room42"
            ROOM_MANIFESTS+=(--manifest "$M25A_BUILD/room42/manifest.json")
        fi
    else
        ROOM_MANIFESTS=(--manifest "$M23A_BUILD/authentic/manifest.json")
        ROOM_BINARY_DIR="$M23A_BUILD/segments"
    fi
    if [[ "${SAME_BUILD_SCUMM_M25A_VALIDATOR:-0}" == "1" ]]; then
        :
    elif [[ "${SAME_BUILD_SCUMM_M23B:-0}" == "1" ]]; then
        mkdir -p "$M23A_BUILD/authentic-room63"
        ROOM49_GLOBAL_SCRIPTS=(2 144 145)
        if [[ "${SAME_BUILD_SCUMM_M25_MOVEMENT:-0}" == "1" ]]; then
            ROOM49_GLOBAL_SCRIPTS+=(151)
        fi
        VISUAL_ARGS=()
        if [[ "${SAME_BUILD_SCUMM_ROOM_VISUAL:-0}" == "1" ]]; then
            VISUAL_ARGS+=(--visuals 49)
        fi
        ROOM49_ROOMS=(49)
        ROOM49_GLOBAL_ARGS=(--global-scripts "${ROOM49_GLOBAL_SCRIPTS[@]}")
        if [[ "${SAME_BUILD_SCUMM_PHASE6L_A1D:-0}" == "1" ]]; then
            # Authentic producer artifact: retain the canonical boot/title
            # rooms and the complete, source-bound dynamic global closure.
            ROOM49_ROOMS=(49 68 75)
            ROOM49_GLOBAL_ARGS=(--global-script-set phase6la1d)
            ENGINE_SELECTION_ARGS+=(--scumm-title-start-room 75 --scumm-title-target-room 49)
        elif [[ "${SAME_BUILD_SCUMM_PHASE6I:-0}" == "1" ]]; then
            ROOM49_GLOBAL_ARGS=(--global-script-set phase6i)
        elif [[ "${SAME_BUILD_SCUMM_PHASE6HB:-0}" == "1" ]]; then
            ROOM49_GLOBAL_ARGS=(--global-script-set phase6hb)
        elif [[ "${SAME_BUILD_SCUMM_PHASE6HA:-0}" == "1" ]]; then
            ROOM49_GLOBAL_ARGS=(--global-script-set phase6ha)
        fi
        "$PYTHON" tools/cook_scumm_v5_rooms.py \
            --archive "$M23A_SOURCE" \
            --profile examples/profiles/templates/fate_of_atlantis_demo.json \
            --rooms "${ROOM49_ROOMS[@]}" "${ROOM49_GLOBAL_ARGS[@]}" --executable \
            "${VISUAL_ARGS[@]}" --output-dir "$M23A_BUILD/authentic"
        ROOM63_ARGS=(--rooms 63)
        if [[ "${SAME_BUILD_SCUMM_M23C:-0}" == "1" ]]; then
            ROOM63_ARGS+=(--global-scripts 151 --executable)
        fi
        "$PYTHON" tools/cook_scumm_v5_rooms.py \
            --archive "$M23A_SOURCE" \
            --profile examples/profiles/templates/fate_of_atlantis_demo.json \
            "${ROOM63_ARGS[@]}" --output-dir "$M23A_BUILD/authentic-room63"
        ROOM_MANIFESTS+=(--manifest "$M23A_BUILD/authentic-room63/manifest.json")
    else
        "$PYTHON" tools/cook_scumm_v5_rooms.py \
            --archive "$M23A_SOURCE" \
            --profile examples/profiles/templates/fate_of_atlantis_demo.json \
            --rooms 49 63 --output-dir "$M23A_BUILD/authentic"
    fi
    if [[ "${SAME_BUILD_SCUMM_M25A_VALIDATOR:-0}" != "1" ]]; then
        "$PYTHON" tools/build_m23a_lifecycle_rooms.py \
            --output-dir "$M23A_BUILD/lifecycle"
    fi
    ROOM_GENERATOR_ARGS=()
    if [[ "${SAME_BUILD_SCUMM_M25A_VALIDATOR:-0}" == "1" ]]; then
        if [[ "${SAME_BUILD_SCUMM_SCENARIO_FIXTURE:-0}" == "1" ]]; then
            if [[ "${SAME_M25A_VALIDATOR_CASE:-}" == "fishnet" ]]; then
                ROOM_GENERATOR_ARGS+=(--executable-local-room 49 --executable-local-object 49:595 --far-programs --far-validator-output runtime/snes/generated/scumm_v5_room_validator_far.inc.pasm)
            elif [[ "${SAME_M25A_VALIDATOR_CASE:-}" == "balloon" ]]; then
                ROOM_GENERATOR_ARGS+=(--executable-local-room 49 --executable-local-object 49:593 --far-programs --far-validator-output runtime/snes/generated/scumm_v5_room_validator_far.inc.pasm)
            elif [[ "${SAME_M25A_VALIDATOR_CASE:-}" == "salvage" ]]; then
                ROOM_GENERATOR_ARGS+=(--executable-local-room 49 --executable-local-object 49:592 --far-programs --far-validator-output runtime/snes/generated/scumm_v5_room_validator_far.inc.pasm)
            elif [[ "${SAME_M25A_VALIDATOR_CASE:-}" == "startup42" ]]; then
                # The startup root executes authored ENCD scripts which start
                # room-local scripts in rooms 68, 75, 1, and 42.  Keep the
                # complete local-script directories for this scenario; an
                # entry-only room would silently omit those dependencies.
                ROOM_GENERATOR_ARGS+=(--entry-only-room 1 --entry-only-room 42 --entry-only-room 49 --entry-only-room 68 --entry-only-room 75 --entry-only-room 82
                                      --executable-local 68:200 --executable-local 68:201
                                      # Retain the complete room-42 local-script cone.  The
                                      # switch/hoist sequence crosses several authored local
                                      # continuations (including 201, 202, 207, and 212); partial
                                      # retention turns valid source control flow into a no-op.
                                      --executable-local 42:200 --executable-local 42:201 --executable-local 42:202
                                      --executable-local 42:203 --executable-local 42:204 --executable-local 42:205
                                      --executable-local 42:206 --executable-local 42:207 --executable-local 42:208
                                      --executable-local 42:209 --executable-local 42:210 --executable-local 42:211
                                      --executable-local 42:212 --executable-local 42:213
                                      --executable-local-object 42:493
                                      --executable-local-object 42:492
                                      --executable-local-object 42:490
                                      # The repaired diving-suit action is object 491 verb 8.
                                      # Script 2 reaches this OBCD after its authored movement/wait;
                                      # retain the complete source object rather than letting a
                                      # resource-closure omission turn that handoff into a no-op.
                                      --executable-local-object 42:491
                                      # Object 500's authored verb-8 handler starts object 497
                                      # (the hoist) as its nested continuation.
                                      --executable-local-object 42:497
                                      --executable-local-object 42:500
                                      --far-programs --far-validator-output runtime/snes/generated/scumm_v5_room_validator_far.inc.pasm)
                if [[ -n "${SAME_SCUMM_SCENARIO_CLASS_OVERLAY:-}" ]]; then
                    IFS=',' read -r -a SCENARIO_CLASS_OVERLAYS <<< "${SAME_SCUMM_SCENARIO_CLASS_OVERLAY}"
                    for overlay in "${SCENARIO_CLASS_OVERLAYS[@]}"; do
                        ROOM_GENERATOR_ARGS+=(--scenario-class-overlay "$overlay")
                    done
                fi
                if [[ -n "${SAME_SCUMM_SCENARIO_BIT_OVERLAY:-}" ]]; then
                    IFS=',' read -r -a SCENARIO_BIT_OVERLAYS <<< "${SAME_SCUMM_SCENARIO_BIT_OVERLAY}"
                    for overlay in "${SCENARIO_BIT_OVERLAYS[@]}"; do
                        ROOM_GENERATOR_ARGS+=(--scenario-bit-overlay "$overlay")
                    done
                fi
                if [[ -n "${SAME_SCUMM_SCENARIO_STATE_OVERLAY:-}" ]]; then
                    IFS=',' read -r -a SCENARIO_STATE_OVERLAYS <<< "${SAME_SCUMM_SCENARIO_STATE_OVERLAY}"
                    for overlay in "${SCENARIO_STATE_OVERLAYS[@]}"; do
                        ROOM_GENERATOR_ARGS+=(--scenario-state-overlay "$overlay")
                    done
                fi
            else
                ROOM_GENERATOR_ARGS+=(--executable-local-room 49 --executable-local-object 49:594 --far-programs --far-validator-output runtime/snes/generated/scumm_v5_room_validator_far.inc.pasm)
            fi
        else
            ROOM_GENERATOR_ARGS+=(--entry-only-room 49 --executable-local-room 49)
        fi
    elif [[ "${SAME_BUILD_SCUMM_M23B:-0}" == "1" ]]; then
        # Room 63 is an entry-only transition target, but its authored player
        # objects are executable after the transition.  Keep its OBCD/local
        # directory in the ROM so normal sentence dispatch can resolve those
        # objects; room 49 remains the only room whose locals are needed by
        # the earlier transition lifecycle.
        ROOM_GENERATOR_ARGS+=(--entry-only-room 49 --entry-only-room 68 --entry-only-room 75 --entry-only-room 63 --executable-local-room 49 --executable-local-object 49:596 --executable-local 63:201 --executable-local 63:202 --executable-local-object 63:851 --executable-local-object 63:853 --executable-local-object 63:854 --executable-local-object 63:855 --far-programs)
        if [[ "${SAME_BUILD_SCUMM_PHASE6HB:-0}" == "1" ]]; then
            ROOM_GENERATOR_ARGS+=(--long-object-fail-branch)
        fi
        if [[ "${SAME_BUILD_SCUMM_M23C:-0}" == "1" ]]; then
            ROOM_GENERATOR_ARGS+=(--entry-exit-room 49 --entry-only-room 63)
            if [[ "${SAME_BUILD_M24RB:-0}" == "1" || "${SAME_BUILD_SCUMM_PHASE6HB:-0}" == "1" ]]; then
                ROOM_GENERATOR_ARGS+=(--far-validator-output runtime/snes/generated/scumm_v5_room_validator_far.inc.pasm)
            fi
        fi
    fi
    if [[ "${SAME_BUILD_SCUMM_M25A_VALIDATOR:-0}" != "1" && "${SAME_BUILD_SCUMM_M23C:-0}" != "1" ]]; then
        ROOM_MANIFESTS+=(--manifest "$M23A_BUILD/lifecycle/manifest.json")
    fi
    "$PYTHON" tools/generate_snes_cooked_rooms.py \
        "${ROOM_MANIFESTS[@]}" \
        --output runtime/snes/generated/scumm_v5_rooms.inc.pasm \
        --data-output runtime/snes/generated/scumm_v5_room_data.inc.pasm \
        --binary-dir "$ROOM_BINARY_DIR" \
        "${ROOM_GENERATOR_ARGS[@]}"
    if [[ "${SAME_BUILD_SCUMM_ROOM_VISUAL:-0}" == "1" ]]; then
        ROOM_VISUAL_MANIFEST="${SAME_SCUMM_ROOM_VISUAL_MANIFEST:-$M23A_BUILD/authentic/manifest.json}"
        "$PYTHON" tools/generate_snes_room_visuals.py \
            --manifest "$ROOM_VISUAL_MANIFEST" \
            --output runtime/snes/generated/scumm_v5_room_visuals.inc.pasm \
            --binary-dir "$M23A_BUILD/visual-segments" \
            --report "${SAME_SNES_OUTPUT:-build/same-engine-host.sfc}.room-visuals.json" \
            --first-bank 16
    fi
fi
"$PYTHON" tools/generate_snes_engine_selection.py "${ENGINE_SELECTION_ARGS[@]}"
if [[ "${SAME_BUILD_SCUMM_PHASE6HB:-0}" == "1" ]]; then
    "$PYTHON" tools/generate_snes_scumm_variables.py \
        --archive "${SAME_FATE_DEMO_ARCHIVE:-/home/chad/fatedemo-box.zip}" \
        --profile examples/profiles/templates/fate_of_atlantis_demo.json \
        --include runtime/snes/generated/scumm_v5_variables.inc.pasm \
        --manifest "${SAME_SNES_OUTPUT:-build/same-snes-demo.sfc}.variables.json"
fi
SAME_SNES_CARRIER="${SAME_SNES_CARRIER:-lorom}"
if [[ "$SAME_SNES_CARRIER" != "lorom" && "$SAME_SNES_CARRIER" != "sa1_bwram" ]]; then
    echo "Unsupported SAME_SNES_CARRIER: $SAME_SNES_CARRIER" >&2
    exit 1
fi
SAME_SNES_VIDEO_BACKEND="${SAME_SNES_VIDEO_BACKEND:-legacy_backdrop}"
if [[ "$SAME_SNES_VIDEO_BACKEND" != "legacy_backdrop" && "$SAME_SNES_VIDEO_BACKEND" != "mode3_surface" ]]; then
    echo "Unsupported SAME_SNES_VIDEO_BACKEND: $SAME_SNES_VIDEO_BACKEND" >&2
    exit 1
fi
if [[ "$SAME_SNES_VIDEO_BACKEND" == "mode3_surface" && "$SAME_SNES_CARRIER" != "sa1_bwram" ]]; then
    echo "mode3_surface requires SAME_SNES_CARRIER=sa1_bwram" >&2
    exit 1
fi
SAME_SNES_VIDEO_OVERLAY="${SAME_SNES_VIDEO_OVERLAY:-none}"
if [[ "$SAME_SNES_VIDEO_OVERLAY" != "none" && "$SAME_SNES_VIDEO_OVERLAY" != "bg2_index4" ]]; then
    echo "Unsupported SAME_SNES_VIDEO_OVERLAY: $SAME_SNES_VIDEO_OVERLAY" >&2
    exit 1
fi
if [[ "$SAME_SNES_VIDEO_OVERLAY" == "bg2_index4" && ( "$SAME_SNES_CARRIER" != "sa1_bwram" || "$SAME_SNES_VIDEO_BACKEND" != "mode3_surface" ) ]]; then
    echo "bg2_index4 requires sa1_bwram + mode3_surface" >&2
    exit 1
fi
SAME_SNES_OUTPUT="${SAME_SNES_OUTPUT:-build/same-engine-host.sfc}"
CARRIER_MANIFEST="${SAME_SNES_OUTPUT%.sfc}.carrier.json"
VIDEO_BACKEND_MANIFEST="${SAME_SNES_OUTPUT%.sfc}.video-backend.json"
VIDEO_OVERLAY_MANIFEST="${SAME_SNES_OUTPUT%.sfc}.video-overlay.json"
CARRIER_ARGS=(--carrier "$SAME_SNES_CARRIER" --manifest "$CARRIER_MANIFEST")
if [[ -n "${SAME_SNES_ROM_SIZE_CODE:-}" ]]; then
    CARRIER_ARGS+=(--rom-size-code "$SAME_SNES_ROM_SIZE_CODE")
elif [[ "$SAME_SNES_CARRIER" == "sa1_bwram" || "${SAME_BUILD_SCUMM_M23A:-0}" == "1" ]]; then
    CARRIER_ARGS+=(--rom-size-code 0x09)
else
    CARRIER_ARGS+=(--rom-size-code 0x07)
fi
if [[ "${SAME_BUILD_SCUMM_M20:-0}" == "1" ]]; then
    CARRIER_ARGS+=(--save-enabled)
fi
"$PYTHON" tools/generate_snes_carrier.py "${CARRIER_ARGS[@]}"
"$PYTHON" tools/generate_snes_video_backend.py \
    --backend "$SAME_SNES_VIDEO_BACKEND" --carrier "$SAME_SNES_CARRIER" \
    --manifest "$VIDEO_BACKEND_MANIFEST"
"$PYTHON" tools/generate_snes_video_overlay.py \
    --overlay "$SAME_SNES_VIDEO_OVERLAY" --carrier "$SAME_SNES_CARRIER" \
    --backend "$SAME_SNES_VIDEO_BACKEND" --manifest "$VIDEO_OVERLAY_MANIFEST"
if [[ "$SAME_SNES_VIDEO_OVERLAY" == "bg2_index4" ]]; then
    if [[ "${SAME_SNES_ENGINE:-demo}" != "scumm_v5" ]]; then
        echo "bg2_index4 production subtitle overlay currently requires scumm_v5" >&2
        exit 1
    fi
    "$PYTHON" tools/generate_snes_scumm_charset.py \
        --archive "${SAME_FATE_DEMO_ARCHIVE:-/home/chad/fatedemo-box.zip}" \
        --profile "${SAME_SNES_PROFILE:-examples/profiles/templates/fate_of_atlantis_demo.json}" \
        --output build/generated/scumm-v5-font0.sc5fnt \
        --include runtime/snes/generated/scumm_v5_font.inc.pasm \
        --manifest "${SAME_SNES_OUTPUT%.sfc}.charset.json"
else
    printf '%s\n' '; Generated empty SCUMM charset include.' > runtime/snes/generated/scumm_v5_font.inc.pasm
fi
if [[ "${SAME_BUILD_SCUMM_M20:-0}" == "1" ]]; then
    if [[ -z "${SAME_SNES_PROFILE:-}" ]]; then
        echo "SAME_SNES_PROFILE is required for the M20 save identity" >&2
        exit 1
    fi
    SAVE_ID_ARGS=()
    if [[ "${SAME_BUILD_SCUMM_M22:-0}" == "1" ]]; then
        SAVE_ID_ARGS+=(--sections audio/fate_s6/m22_sound80/audit.json)
    fi
    "$PYTHON" tools/generate_snes_save_identity.py \
        --profile "$SAME_SNES_PROFILE" --catalog "$SAME_MUSIC_CATALOG" \
        --logical-id "${SAME_SCUMM_SAVE_LOGICAL_ID:-154}" \
        "${SAVE_ID_ARGS[@]}" \
        --output runtime/snes/generated/save_identity.inc.pasm
fi
"$PYTHON" tools/lint_poppy.py runtime/snes/main.pasm
mkdir -p build
SAME_SNES_MAP="${SAME_SNES_OUTPUT%.sfc}.map"
SAME_SNES_LISTING="${SAME_SNES_OUTPUT%.sfc}.lst"
DOTNET_ROOT="$DOTNET_ROOT" PATH="$DOTNET_ROOT:$PATH" \
    dotnet "$POPPY_DLL" -t snes -I runtime/snes \
    runtime/snes/main.pasm -o "$SAME_SNES_OUTPUT" \
    -m "$SAME_SNES_MAP" -l "$SAME_SNES_LISTING" --no-verify
echo "SNES layout map: $SAME_SNES_MAP"
"$PYTHON" tools/report_snes_layout.py "$SAME_SNES_MAP"
"$PYTHON" tools/finalize_snes_rom.py "$SAME_SNES_OUTPUT" \
    --carrier "$SAME_SNES_CARRIER" --manifest "$CARRIER_MANIFEST"
"$PYTHON" tools/audit_snes_rom.py "$SAME_SNES_OUTPUT" \
    --carrier "$SAME_SNES_CARRIER" --manifest "$CARRIER_MANIFEST"
sha256sum "$SAME_SNES_OUTPUT"

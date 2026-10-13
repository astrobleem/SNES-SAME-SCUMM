#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
POPPY_ROOT="${POPPY_ROOT:-/home/chad/poppy-jsl-address-fix}"
DOTNET_ROOT="${DOTNET_ROOT:-/home/chad/.dotnet10}"
POPPY_DLL="${POPPY_DLL:-$POPPY_ROOT/src/Poppy.CLI/bin/Release/net10.0/poppy.dll}"
PYTHON="${PYTHON:-python3}"
SAME_MUSIC_CATALOG="${SAME_MUSIC_CATALOG:-$ROOT/audio/m24ra/catalog.json}"
SAME_TAD_LAYOUT_OUTPUT="${SAME_TAD_LAYOUT_OUTPUT:-runtime/snes/generated/tad_layout.inc.pasm}"
SAME_TAD_DONOR_DIR="${SAME_TAD_DONOR_DIR:-$ROOT/../terrific-audio-driver}"
SAME_FATE_ARCHIVE="${SAME_FATE_ARCHIVE:-${SAME_FATE_DEMO_ARCHIVE:-}}"
SAME_FATE_DEMO_ARCHIVE="${SAME_FATE_DEMO_ARCHIVE:-$SAME_FATE_ARCHIVE}"

# The authentic-startup diagnostic reuses the source-backed resource/profile
# selection from the M25A startup case without compiling M25A's trace and
# breakpoint instrumentation into the runtime. This keeps a cold-start
# gameplay ROM distinct from the larger validator personality.
M25A_CONTENT_PROFILE="${SAME_BUILD_SCUMM_M25A_VALIDATOR:-0}"
M25A_PROFILE_CASE="${SAME_M25A_VALIDATOR_CASE:-normal}"
if [[ "${SAME_SNES_ENGINE:-demo}" == "winston_io" ]]; then
    # The package/audio diagnostic is not a Fate build and does not consume a
    # game profile. Keep its build identity from implying otherwise.
    SAME_FATE_PROFILE="${SAME_FATE_PROFILE-}"
    SAME_SNES_PROFILE="${SAME_SNES_PROFILE-}"
elif [[ "${SAME_BUILD_SCUMM_AUTHENTIC_STARTUP:-0}" == "1" ]]; then
    if [[ "${SAME_SNES_ENGINE:-demo}" != "scumm_v5" || \
          "${SAME_BUILD_SCUMM_M23A:-0}" != "1" || \
          "${SAME_BUILD_SCUMM_M25A_VALIDATOR:-0}" == "1" ]]; then
        echo "Authentic-startup profile requires SCUMM v5 room services; scenario-state fixtures and M25A instrumentation must be disabled" >&2
        exit 1
    fi
    M25A_CONTENT_PROFILE=1
    M25A_PROFILE_CASE=startup42
    SAME_FATE_PROFILE="${SAME_FATE_PROFILE:-examples/profiles/templates/fate_of_atlantis_dos_cd.json}"
else
SAME_FATE_PROFILE="${SAME_FATE_PROFILE:-examples/profiles/templates/fate_of_atlantis_demo.json}"
fi
if [[ "${SAME_SNES_ENGINE:-demo}" != "winston_io" ]]; then
    SAME_SNES_PROFILE="${SAME_SNES_PROFILE:-$SAME_FATE_PROFILE}"
fi
export SAME_FATE_ARCHIVE SAME_FATE_DEMO_ARCHIVE SAME_FATE_PROFILE SAME_SNES_PROFILE

if [[ "${SAME_BUILD_SCUMM_DYNAMIC_PROGRAM_RESIDENCY:-0}" == "1" ]]; then
    if [[ "${SAME_SNES_ENGINE:-demo}" != "scumm_v5" ||
          "${SAME_BUILD_SCUMM_M23A:-0}" != "1" ||
          "${SAME_BUILD_M24RB:-0}" != "1" ]]; then
        echo "Dynamic SCUMM residency requires the SCUMM v5 M23A + M24RB room-service build" >&2
        exit 1
    fi
    "$PYTHON" "$ROOT/tools/audit_scumm_residency_wram.py" \
        --output "${SAME_SNES_OUTPUT:-build/scumm-dynamic-residency.sfc}.wram.json"
    if [[ -n "${SAME_SCUMM_DYNAMIC_BOOT_SCRIPT:-}" &&
          ! "${SAME_SCUMM_DYNAMIC_BOOT_SCRIPT}" =~ ^[0-9]+$ ]]; then
        echo "SAME_SCUMM_DYNAMIC_BOOT_SCRIPT must be an unsigned script number" >&2
        exit 1
    fi
    if [[ -n "${SAME_SCUMM_DYNAMIC_BOOT_SCRIPT:-}" &&
          "${SAME_SCUMM_DYNAMIC_BOOT_SCRIPT}" -gt 255 ]]; then
        echo "SAME_SCUMM_DYNAMIC_BOOT_SCRIPT must fit the SCUMM v5 script byte" >&2
        exit 1
    fi
fi
if [[ "${SAME_BUILD_SCUMM_MSU1_PROGRAMS:-0}" == "1" ]]; then
    if [[ "${SAME_SNES_ENGINE:-demo}" != "scumm_v5" ||
          "${SAME_BUILD_SCUMM_DYNAMIC_PROGRAM_RESIDENCY:-0}" != "1" ||
          "${SAME_BUILD_SCUMM_M23A:-0}" != "1" ||
          "${SAME_BUILD_M24RB:-0}" != "1" ]]; then
        echo "MSU-backed SCUMM ProgramUnits require SCUMM v5, dynamic residency, M23A, and M24RB" >&2
        exit 1
    fi
    if [[ -n "${SAME_BUILD_SCUMM_EMBEDDED_TEST_PROGRAMS:-0}" &&
          "${SAME_BUILD_SCUMM_EMBEDDED_TEST_PROGRAMS:-0}" != "0" ]]; then
        echo "MSU-backed SCUMM builds cannot retain embedded test-program fallback" >&2
        exit 1
    fi
fi
if [[ "${SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES:-0}" == "1" ]]; then
    if [[ "${SAME_BUILD_SCUMM_MSU1_PROGRAMS:-0}" != "1" ||
          "${SAME_SNES_CARRIER:-lorom}" != "sa1_bwram" ||
          "${SAME_SNES_VIDEO_BACKEND:-legacy_backdrop}" != "mode3_surface" ||
          "${SAME_BUILD_SCUMM_ROOM_VISUAL:-0}" != "1" ]]; then
        echo "Live MSU room resources require MSU ProgramUnits, SA-1 BW-RAM, mode3_surface, and room visuals" >&2
        exit 1
    fi
fi
if [[ -n "${SAME_MSU1_LIVE_ROOM_PCM_TRACK:-}" ]]; then
    if [[ "${SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES:-0}" != "1" ||
          "${SAME_BUILD_SCUMM_MSU1_PROGRAMS:-0}" != "1" ||
          ! "${SAME_MSU1_LIVE_ROOM_PCM_TRACK}" =~ ^[0-9]+$ ||
          "${SAME_MSU1_LIVE_ROOM_PCM_TRACK}" -lt 1 ||
          "${SAME_MSU1_LIVE_ROOM_PCM_TRACK}" -gt 65535 ||
          -z "${SAME_MSU1_LIVE_ROOM_PCM_SOURCE:-}" ||
          ! -f "${SAME_MSU1_LIVE_ROOM_PCM_SOURCE}" ]]; then
        echo "MSU room PCM test needs live-room SCUMM mode, a track in 1..65535, and an existing SAME_MSU1_LIVE_ROOM_PCM_SOURCE" >&2
        exit 1
    fi
fi
if [[ -n "${SAME_SCUMM_WHOLE_SOURCE_MANIFEST:-}" &&
      "${SAME_BUILD_SCUMM_DYNAMIC_PROGRAM_RESIDENCY:-0}" != "1" ]]; then
    echo "SAME_SCUMM_WHOLE_SOURCE_MANIFEST requires dynamic SCUMM program residency" >&2
    exit 1
fi
if [[ "${SAME_SCUMM_PACK_SOURCE_TABLES:-0}" != "0" &&
      "${SAME_SCUMM_PACK_SOURCE_TABLES:-0}" != "1" ]]; then
    echo "SAME_SCUMM_PACK_SOURCE_TABLES must be 0 or 1" >&2
    exit 1
fi
if [[ "${SAME_BUILD_SCUMM_DYNAMIC_FATE_EXPERIMENT:-0}" == "1" ]]; then
    if [[ "${SAME_BUILD_SCUMM_DYNAMIC_PROGRAM_RESIDENCY:-0}" != "1" ||
          "${SAME_BUILD_SCUMM_AUTHENTIC_STARTUP:-0}" != "1" ||
          "${SAME_BUILD_SCUMM_CONTROLLER:-0}" != "1" ]]; then
        echo "Dynamic FATE experiment requires dynamic residency, authentic startup, and the normal controller" >&2
        exit 1
    fi
    if [[ "${SAME_FATE_PROFILE:-}" != "examples/profiles/templates/fate_of_atlantis_dos_cd.json" ]]; then
        echo "Dynamic FATE experiment requires the canonical DOS-CD profile" >&2
        exit 1
    fi
    if [[ -z "${SAME_FATE_ARCHIVE:-}" ]]; then
        echo "Dynamic FATE experiment requires SAME_FATE_ARCHIVE" >&2
        exit 1
    fi
fi
if [[ "${SAME_BUILD_SCUMM_RESIDENCY_DIAGNOSTIC:-0}" == "1" &&
      "${SAME_BUILD_SCUMM_DYNAMIC_PROGRAM_RESIDENCY:-0}" != "1" ]]; then
    echo "SCUMM residency diagnostic requires SAME_BUILD_SCUMM_DYNAMIC_PROGRAM_RESIDENCY=1" >&2
    exit 1
fi

cd "$ROOT"
export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
mkdir -p runtime/snes/generated
# Builds must own the complete generated engine-fixture include set instead
# of accidentally depending on stale files in runtime/snes/generated.
"$PYTHON" tools/generate_engine_fixtures.py
"$PYTHON" tools/check_poppy.py "$POPPY_ROOT" --dll "$POPPY_DLL"
POPPY_SHA256="$(sha256sum "$POPPY_DLL" | awk '{print $1}')"
echo "Poppy SHA-256: $POPPY_SHA256"
"$PYTHON" -m same.cli abi generate runtime/snes/generated/abi.inc.pasm
mkdir -p build/audio
if [[ -z "${SAME_TAD_PREBUILT_DIR:-}" ]]; then
    "$PYTHON" tools/build_m24ra_tad_toolchain.py \
        --donor "$SAME_TAD_DONOR_DIR" --output build/toolchain/tad-m24ra
    "$PYTHON" tools/build_m24ra_fixture.py \
        --compiler build/toolchain/tad-m24ra/target/release/tad-compiler \
        --output build/profile-music/m24ra
    SAME_TAD_PREBUILT_DIR="$ROOT/build/profile-music/m24ra"
    SAME_BUILD_M24RA="${SAME_BUILD_M24RA:-1}"
fi
if [[ -n "${SAME_TAD_PREBUILT_DIR:-}" ]]; then
    PREBUILT_DIR="$(cd "$SAME_TAD_PREBUILT_DIR" && pwd)"
    if [[ ! -f "$PREBUILT_DIR/tad.bin" || ! -f "$PREBUILT_DIR/tad.inc" ]]; then
        echo "Prebuilt TAD directory must contain tad.bin and tad.inc: $PREBUILT_DIR" >&2
        exit 1
    fi
    cp "$PREBUILT_DIR/tad.bin" build/audio/tad.bin
    cp "$PREBUILT_DIR/tad.inc" build/audio/tad.inc
    cp "$PREBUILT_DIR/tad.asm" build/audio/tad.asm
    echo "Using prebuilt TAD data: $PREBUILT_DIR"
fi
"$PYTHON" tools/generate_fate_tad_layout.py \
    build/audio/tad.bin build/audio/tad.inc \
    runtime/snes/generated/tad_layout.inc.pasm \
    --assembly build/audio/tad.asm
if [[ "$SAME_TAD_LAYOUT_OUTPUT" != "runtime/snes/generated/tad_layout.inc.pasm" ]]; then
    "$PYTHON" tools/generate_fate_tad_layout.py \
        build/audio/tad.bin build/audio/tad.inc "$SAME_TAD_LAYOUT_OUTPUT" \
        --assembly build/audio/tad.asm
fi
"$PYTHON" tools/generate_music_catalog.py \
    "$SAME_MUSIC_CATALOG" build/audio/tad.inc \
    runtime/snes/generated/music_catalog.inc.pasm \
    --lifecycle-output runtime/snes/generated/music_lifecycle_catalog.inc.pasm \
    $([[ "${SAME_BUILD_SCUMM_PHASE6L_A1D:-0}" == "1" ]] && echo --exclude-compiled-song fate_sound_80_default --exclude-compiled-song fate_sound_80_hook14)
ENGINE_SELECTION_ARGS=(--engine "${SAME_SNES_ENGINE:-demo}")
if [[ "${SAME_BUILD_SCUMM_EMBEDDED_TEST_PROGRAMS:-1}" != "0" &&
      "${SAME_BUILD_SCUMM_EMBEDDED_TEST_PROGRAMS:-1}" != "1" ]]; then
    echo "SAME_BUILD_SCUMM_EMBEDDED_TEST_PROGRAMS must be 0 or 1" >&2
    exit 1
fi
if [[ "${SAME_BUILD_SCUMM_EMBEDDED_TEST_PROGRAMS:-1}" == "0" ]]; then
    if [[ "${SAME_SNES_ENGINE:-demo}" != "scumm_v5" ||
          "${SAME_BUILD_SCUMM_M23A:-0}" != "1" ]]; then
        echo "Disabling embedded SCUMM test programs requires SCUMM v5 source-backed M23A programs" >&2
        exit 1
    fi
    ENGINE_SELECTION_ARGS+=(--scumm-disable-embedded-test-programs)
fi
if [[ "${SAME_BUILD_M24RA:-0}" == "1" ]]; then
    ENGINE_SELECTION_ARGS+=(--m24ra)
fi
if [[ "${SAME_BUILD_M24RB:-0}" == "1" ]]; then
    ENGINE_SELECTION_ARGS+=(--m24rb --m24rb-phase-delay "${SAME_M24RB_PHASE_DELAY:-125}")
fi
if [[ "${SAME_BUILD_RESET_DIAGNOSTICS:-1}" == "0" ]]; then
    ENGINE_SELECTION_ARGS+=(--disable-reset-diagnostics)
fi
if [[ "${SAME_BUILD_CAPTURE_FIRST_BRK:-0}" == "1" ]]; then
    if [[ "${SAME_BUILD_RESET_DIAGNOSTICS:-1}" == "0" ]]; then
        echo "First-BRK capture requires reset diagnostic storage" >&2
        exit 1
    fi
    ENGINE_SELECTION_ARGS+=(--capture-first-brk)
fi
if [[ "${SAME_BUILD_SCUMM_M23C_CLASS_CONFORMANCE:-0}" == "1" ]]; then
    ENGINE_SELECTION_ARGS+=(--scumm-m23c-class-conformance)
fi
if [[ "${SAME_BUILD_SCUMM_M25A_VALIDATOR:-0}" == "1" ]]; then
    ENGINE_SELECTION_ARGS+=(--scumm-m25a-validator)
fi
if [[ "${SAME_BUILD_SCUMM_M25A_PENDING_ONLY:-0}" == "1" ]]; then
    if [[ "${SAME_BUILD_SCUMM_M25A_VALIDATOR:-0}" != "1" || \
          "${SAME_M25A_VALIDATOR_CASE:-}" != "pending-room-request" || \
          "${SAME_BUILD_SCUMM_SCENARIO_FIXTURE:-0}" == "1" ]]; then
        echo "M25A pending-only mode requires its validator content case and no broad scenario fixture" >&2
        exit 1
    fi
    ENGINE_SELECTION_ARGS+=(--scumm-m25a-pending-only)
fi
if [[ "${SAME_BUILD_SCUMM_SCENARIO_FIXTURE:-0}" == "1" ]]; then
    ENGINE_SELECTION_ARGS+=(--scumm-scenario-fixture)
    if [[ -n "${SAME_SCUMM_SCENARIO_START_ROOM:-}" ]]; then
        ENGINE_SELECTION_ARGS+=(--scumm-scenario-start-room "${SAME_SCUMM_SCENARIO_START_ROOM}")
    elif [[ "${SAME_M25A_VALIDATOR_CASE:-}" == "room55" ]]; then
        ENGINE_SELECTION_ARGS+=(--scumm-scenario-start-room 55)
    elif [[ "${SAME_M25A_VALIDATOR_CASE:-}" == "room55-movement" ]]; then
        ENGINE_SELECTION_ARGS+=(--scumm-scenario-start-room 49)
    elif [[ "$M25A_PROFILE_CASE" == "startup42" ]]; then
        # Start in the explicit, corpus-checked synthetic bootstrap room. Its
        # ENCD starts only authentic Global1; Global1 starts its authored
        # Global75/Global18 children at their own call sites.
        ENGINE_SELECTION_ARGS+=(--scumm-scenario-start-room 254)
    fi
fi
if [[ "${SAME_BUILD_SCUMM_AUTHENTIC_STARTUP:-0}" == "1" ]]; then
    ENGINE_SELECTION_ARGS+=(--scumm-authentic-boot-script 1 --scumm-authentic-boot-argument=-7873)
fi
if [[ "${SAME_BUILD_SCUMM_DYNAMIC_PROGRAM_RESIDENCY:-0}" == "1" &&
      -n "${SAME_SCUMM_DYNAMIC_BOOT_SCRIPT:-}" ]]; then
    ENGINE_SELECTION_ARGS+=(--scumm-authentic-boot-script "${SAME_SCUMM_DYNAMIC_BOOT_SCRIPT}"
        --scumm-authentic-boot-argument "${SAME_SCUMM_DYNAMIC_BOOT_ARGUMENT:-0}")
fi
if [[ -n "${SAME_SCUMM_TITLE_START_ROOM:-}" ||
      -n "${SAME_SCUMM_TITLE_TARGET_ROOM:-}" ]]; then
    if [[ -z "${SAME_SCUMM_TITLE_START_ROOM:-}" ||
          -z "${SAME_SCUMM_TITLE_TARGET_ROOM:-}" ]]; then
        echo "SCUMM title START routing requires both SAME_SCUMM_TITLE_START_ROOM and SAME_SCUMM_TITLE_TARGET_ROOM" >&2
        exit 1
    fi
    ENGINE_SELECTION_ARGS+=(--scumm-title-start-room "${SAME_SCUMM_TITLE_START_ROOM}"
        --scumm-title-target-room "${SAME_SCUMM_TITLE_TARGET_ROOM}")
fi
if [[ "${SAME_BUILD_SCUMM_M25_MOVEMENT:-0}" == "1" ]]; then
    ENGINE_SELECTION_ARGS+=(--scumm-m25-movement)
fi
if [[ "${SAME_BUILD_SCUMM_PHASE6HB:-0}" == "1" ]]; then
    ENGINE_SELECTION_ARGS+=(--scumm-phase6hb)
fi
if [[ "${SAME_BUILD_SCUMM_CONTROLLER_CONFORMANCE:-0}" == "1" ]]; then
    : # The shared source/variable include is generated below from this profile.
fi
if [[ "${SAME_BUILD_SCUMM_ROOM_VISUAL:-0}" == "1" ]]; then
    if [[ "${SAME_SNES_CARRIER:-lorom}" != "sa1_bwram" || "${SAME_SNES_VIDEO_BACKEND:-legacy_backdrop}" != "mode3_surface" ]]; then
        echo "SCUMM room visuals require sa1_bwram + mode3_surface" >&2
        exit 1
    fi
    ENGINE_SELECTION_ARGS+=(--scumm-room-visual)
fi
if [[ "${SAME_BUILD_SCUMM_CONTROLLER:-0}" == "1" || "${SAME_BUILD_SCUMM_CONTROLLER_FIXTURE:-0}" == "1" ]]; then
    ENGINE_SELECTION_ARGS+=(--scumm-controller)
fi
if [[ "${SAME_BUILD_SCUMM_CONTROLLER_CONFORMANCE:-0}" == "1" ]]; then
    ENGINE_SELECTION_ARGS+=(--scumm-controller-conformance)
    if [[ "${SAME_BUILD_SCUMM_CONTROLLER_CONFORMANCE_NO_ROOT_ROOM:-0}" == "1" ]]; then
        ENGINE_SELECTION_ARGS+=(--scumm-controller-conformance-no-root-room)
    fi
    if [[ "${SAME_BUILD_SCUMM_C19_NATIVE_FIXTURE:-0}" == "1" ]]; then
        ENGINE_SELECTION_ARGS+=(--scumm-c19-native-fixture)
    fi
    if [[ "${SAME_BUILD_SCUMM_CONTROLLER:-0}" == "1" ]]; then
        ENGINE_SELECTION_ARGS+=(--scumm-controller)
    fi
fi
if [[ "${SAME_BUILD_SCUMM_CONTROLLER_FIXTURE:-0}" == "1" ]]; then
    ENGINE_SELECTION_ARGS+=(--scumm-controller-fixture)
    ENGINE_SELECTION_ARGS+=(--scumm-controller-behavior-mask "${SAME_SCUMM_CONTROLLER_BEHAVIOR_MASK:-7}")
    if [[ "${SAME_SCUMM_CONTROLLER_WITNESS:-1}" != "0" ]]; then
        ENGINE_SELECTION_ARGS+=(--scumm-controller-witness)
    fi
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
ROOM_TABLES_GENERATED=0
if [[ "${SAME_BUILD_SCUMM_M23A:-0}" == "1" || "${SAME_BUILD_SCUMM_CONTROLLER_CONFORMANCE:-0}" == "1" ]]; then
    if [[ "${SAME_BUILD_SCUMM_M23A:-0}" == "1" ]]; then
        ENGINE_SELECTION_ARGS+=(--scumm-m23a)
    fi
if [[ "${SAME_BUILD_SCUMM_DYNAMIC_PROGRAM_RESIDENCY:-0}" == "1" ]]; then
    ENGINE_SELECTION_ARGS+=(--scumm-dynamic-program-residency)
fi
if [[ "${SAME_BUILD_SCUMM_MSU1_PROGRAMS:-0}" == "1" ]]; then
    ENGINE_SELECTION_ARGS+=(--msu1-storage --scumm-msu1-programs
        --scumm-disable-embedded-test-programs)
fi
if [[ "${SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES:-0}" == "1" ]]; then
    ENGINE_SELECTION_ARGS+=(--scumm-msu1-live-room-resources)
fi
if [[ -n "${SAME_MSU1_LIVE_ROOM_PCM_TRACK:-}" ]]; then
    ENGINE_SELECTION_ARGS+=(--scumm-msu1-live-room-pcm-track
        "$SAME_MSU1_LIVE_ROOM_PCM_TRACK")
fi
if [[ "${SAME_BUILD_SCUMM_RESIDENCY_DIAGNOSTIC:-0}" == "1" ]]; then
    ENGINE_SELECTION_ARGS+=(--scumm-residency-diagnostic)
fi
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
    if [[ "${SAME_BUILD_SCUMM_CONTROLLER_CONFORMANCE:-0}" == "1" ]]; then
        CONFORMANCE_BUILD="$ROOT/build/controller-conformance"
        M23A_BUILD="$CONFORMANCE_BUILD"
        if [[ "${SAME_BUILD_SCUMM_C19_NATIVE_FIXTURE:-0}" == "1" ]]; then
            # The C19 cutscene control enters through the engine's dedicated
            # fixture dispatch. It needs the synthetic variable layout, but
            # no controller-room resources; including room 1 here caused an
            # unrelated room request before the cutscene fixture ran.
            ROOM_MANIFESTS=(--manifest examples/resources/scumm_v5/empty_cooked_rooms.json)
            ROOM_BINARY_DIR="$ROOT/build/empty-scumm-rooms/segments"
            ROOM_GENERATOR_ARGS+=(--far-programs)
        else
            "$PYTHON" tools/build_scumm_controller_conformance.py --output-dir "$CONFORMANCE_BUILD"
            ROOM_MANIFESTS=(--manifest "$CONFORMANCE_BUILD/manifest.json")
            ROOM_BINARY_DIR="$CONFORMANCE_BUILD/segments"
            ROOM_GENERATOR_ARGS+=(--far-programs)
        fi
        if [[ "${SAME_BUILD_SCUMM_ROOM_SERVICE_FAR:-0}" == "1" || "${SAME_BUILD_M24RB:-0}" == "1" || "${SAME_BUILD_SCUMM_PHASE6HB:-0}" == "1" || "${SAME_BUILD_SCUMM_CONTROLLER_CONFORMANCE:-0}" == "1" ]]; then
            ROOM_GENERATOR_ARGS+=(--far-validator-output runtime/snes/generated/scumm_v5_room_validator_far.inc.pasm)
        fi
        mkdir -p "$ROOM_BINARY_DIR"
        if [[ "${SAME_BUILD_SCUMM_C19_NATIVE_FIXTURE:-0}" != "1" ]]; then
            "$PYTHON" tools/generate_snes_room_visuals.py \
                --manifest "$CONFORMANCE_BUILD/manifest.json" \
                --output runtime/snes/generated/scumm_v5_room_visuals.inc.pasm \
                --binary-dir "$CONFORMANCE_BUILD/visual-segments" \
                --report "${SAME_SNES_OUTPUT:-build/controller-conformance.sfc}.room-visuals.json" \
                --first-bank 16 --room 1
            CONFORMANCE_ROOM_GENERATED=1
            SAME_SCUMM_REUSE_COOKED_ROOM_VISUALS=1
        fi
else
    if [[ "${SAME_BUILD_SCUMM_DYNAMIC_PROGRAM_RESIDENCY:-0}" == "1" &&
          "${SAME_BUILD_SCUMM_DYNAMIC_FATE_EXPERIMENT:-0}" != "1" ]]; then
        if [[ -n "${SAME_SCUMM_WHOLE_SOURCE_MANIFEST:-}" ]]; then
            DYNAMIC_RESIDENCY_MANIFEST="$SAME_SCUMM_WHOLE_SOURCE_MANIFEST"
            SOURCE_SCOPE="$("$PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1])).get("source_scope", ""))' "$DYNAMIC_RESIDENCY_MANIFEST")"
            if [[ "$SOURCE_SCOPE" != "ALL_AVAILABLE_EXECUTABLES" ]]; then
                echo "Whole-source manifest does not declare ALL_AVAILABLE_EXECUTABLES" >&2
                exit 1
            fi
            M23A_BUILD="${SAME_SCUMM_WHOLE_SOURCE_BUILD_DIR:-$ROOT/build/scumm-whole-source-backend}"
            ROOM_GENERATOR_ARGS+=(--pack-source-tables --banked-room-directory-data)
        else
            DYNAMIC_RESIDENCY_MANIFEST="${SAME_SCUMM_DYNAMIC_FIXTURE_MANIFEST:?Set SAME_SCUMM_DYNAMIC_FIXTURE_MANIFEST to a generated synthetic cooked-room manifest}"
            M23A_BUILD="${SAME_SCUMM_DYNAMIC_BUILD_DIR:-$ROOT/build/scumm-native-residency}"
        fi
        ROOM_MANIFESTS=(--manifest "$DYNAMIC_RESIDENCY_MANIFEST")
        ROOM_BINARY_DIR="${SAME_SCUMM_DYNAMIC_FIXTURE_BINARY_DIR:-$(dirname "$DYNAMIC_RESIDENCY_MANIFEST")/segments}"
        mkdir -p "$M23A_BUILD" "$ROOM_BINARY_DIR"
    else
    M23A_SOURCE="${SAME_FATE_ARCHIVE:?Set SAME_FATE_ARCHIVE to a user-supplied archive}"
    if [[ "${SAME_BUILD_SCUMM_DYNAMIC_FATE_EXPERIMENT:-0}" == "1" ]]; then
        M23A_BUILD="${SAME_SCUMM_DYNAMIC_FATE_BUILD_DIR:-$ROOT/build/fate-dynamic-residency}"
    else
        M23A_BUILD="${SAME_SCUMM_M23A_BUILD_DIR:-$ROOT/build/m23a-rooms}"
    fi
    mkdir -p "$M23A_BUILD/authentic" "$M23A_BUILD/lifecycle" "$M23A_BUILD/segments"
    if [[ "$M25A_CONTENT_PROFILE" == "1" ]]; then
        if [[ "${SAME_BUILD_SCUMM_AUTHENTIC_STARTUP:-0}" == "1" ]]; then
            M25A_BUILD="${SAME_SCUMM_AUTHENTIC_STARTUP_BUILD_DIR:-$ROOT/build/fate-authentic-startup}"
        else
            M25A_BUILD="$ROOT/build/m25a-validator/$M25A_PROFILE_CASE"
        fi
        mkdir -p "$M25A_BUILD" "$M25A_BUILD/segments"
        M25A_FIXTURE_ROOM_ARGS=()
        if [[ "$M25A_PROFILE_CASE" == "startup42" ]]; then
            # 254 is absent from the authoritative Fate archive's room table;
            # keep the synthetic bootstrap carrier outside the game's room
            # namespace so loadRoom(49) resolves only the authentic room.
            M25A_FIXTURE_ROOM_ARGS+=(--fixture-room 254)
            if [[ "${SAME_BUILD_SCUMM_AUTHENTIC_STARTUP:-0}" == "1" ]]; then
                M25A_FIXTURE_ROOM_ARGS+=(--omit-fixture-room)
            fi
        fi
        "$PYTHON" tools/build_m25a_validator_room.py \
            --case "$M25A_PROFILE_CASE" --output-dir "$M25A_BUILD" \
            "${M25A_FIXTURE_ROOM_ARGS[@]}"
        ROOM_MANIFESTS=(--manifest "$M25A_BUILD/manifest.json")
        ROOM_BINARY_DIR="$M25A_BUILD/segments"
        if [[ "$M25A_PROFILE_CASE" == "startup42" || "$M25A_PROFILE_CASE" == "room55" ]]; then
            # The startup profile contributes source-authentic global bodies;
            # its diagnostic cold root schedules Global1 in the ordinary C4
            # table, so no synthetic room enters the active resource map.
            if [[ "$M25A_PROFILE_CASE" == "room55" ]]; then
                ENGINE_SELECTION_ARGS+=(--scumm-scenario-source-actor-state)
            fi
            mkdir -p "$M25A_BUILD/room42"
            # Keep the established default selection, but let an authentic
            # cold-path run cook only rooms whose execution is established.
            # This is a resource-selection control, not a runtime shortcut:
            # every requested room still resolves from its source-authentic
            # archive resource, and newly reached rooms are added explicitly.
            COOKED_STARTUP_BASE_ROOMS=(1 24 42 49 55 68 75 82 4 5)
            if [[ -n "${SAME_SCUMM_AUTHENTIC_STARTUP_BASE_ROOMS:-}" ]]; then
                IFS=',' read -r -a COOKED_STARTUP_BASE_ROOMS <<< \
                    "${SAME_SCUMM_AUTHENTIC_STARTUP_BASE_ROOMS}"
                declare -A STARTUP_BASE_ROOM_SEEN=()
                for index in "${!COOKED_STARTUP_BASE_ROOMS[@]}"; do
                    room=${COOKED_STARTUP_BASE_ROOMS[$index]}
                    if [[ ! "$room" =~ ^[0-9]+$ ]]; then
                        echo "Invalid authentic startup base room ID: $room" >&2
                        exit 1
                    fi
                    room=$((10#$room))
                    if (( room > 255 )); then
                        echo "Invalid authentic startup base room ID: $room" >&2
                        exit 1
                    fi
                    if [[ -n "${STARTUP_BASE_ROOM_SEEN[$room]:-}" ]]; then
                        echo "Duplicate authentic startup base room ID: $room" >&2
                        exit 1
                    fi
                    STARTUP_BASE_ROOM_SEEN["$room"]=1
                    COOKED_STARTUP_BASE_ROOMS[$index]=$room
                done
                unset STARTUP_BASE_ROOM_SEEN
            fi
            COOKED_STARTUP_ROOMS=("${COOKED_STARTUP_BASE_ROOMS[@]}")
            if [[ -n "${SAME_SCUMM_AUTHENTIC_STARTUP_EXTRA_ROOMS:-}" ]]; then
                IFS=',' read -r -a EXTRA_STARTUP_ROOMS <<< \
                    "${SAME_SCUMM_AUTHENTIC_STARTUP_EXTRA_ROOMS}"
                declare -A STARTUP_ROOM_SEEN=()
                for room in "${COOKED_STARTUP_ROOMS[@]}"; do
                    STARTUP_ROOM_SEEN["$room"]=1
                done
                for room in "${EXTRA_STARTUP_ROOMS[@]}"; do
                    if [[ ! "$room" =~ ^[0-9]+$ ]]; then
                        echo "Invalid authentic startup room ID: $room" >&2
                        exit 1
                    fi
                    room=$((10#$room))
                    if (( room > 255 )); then
                        echo "Invalid authentic startup room ID: $room" >&2
                        exit 1
                    fi
                    if [[ -n "${STARTUP_ROOM_SEEN[$room]:-}" ]]; then
                        echo "Duplicate authentic startup room ID: $room" >&2
                        exit 1
                    fi
                    STARTUP_ROOM_SEEN["$room"]=1
                    COOKED_STARTUP_ROOMS+=("$room")
                done
                unset STARTUP_ROOM_SEEN
            fi
            if [[ -n "${SAME_SCUMM_AUTHENTIC_STARTUP_FINAL_ROOMS:-}" ]]; then
                IFS=',' read -r -a FINAL_STARTUP_ROOMS <<< \
                    "${SAME_SCUMM_AUTHENTIC_STARTUP_FINAL_ROOMS}"
                declare -A FINAL_STARTUP_ROOM_SEEN=()
                for room in "${COOKED_STARTUP_ROOMS[@]}"; do
                    FINAL_STARTUP_ROOM_SEEN["$room"]=1
                done
                for room in "${FINAL_STARTUP_ROOMS[@]}"; do
                    if [[ ! "$room" =~ ^[0-9]+$ ]]; then
                        echo "Invalid final authentic startup room ID: $room" >&2
                        exit 1
                    fi
                    room=$((10#$room))
                    if (( room > 255 )); then
                        echo "Invalid final authentic startup room ID: $room" >&2
                        exit 1
                    fi
                    if [[ -n "${FINAL_STARTUP_ROOM_SEEN[$room]:-}" ]]; then
                        echo "Duplicate final authentic startup room ID: $room" >&2
                        exit 1
                    fi
                    FINAL_STARTUP_ROOM_SEEN["$room"]=1
                    COOKED_STARTUP_ROOMS+=("$room")
                done
                unset FINAL_STARTUP_ROOM_SEEN
            fi
            STARTUP_FULL_ROOM_SEEN=()
            if [[ -n "${SAME_SCUMM_AUTHENTIC_STARTUP_FULL_ROOMS:-}" ]]; then
                IFS=',' read -r -a FULL_STARTUP_ROOMS <<< \
                    "${SAME_SCUMM_AUTHENTIC_STARTUP_FULL_ROOMS}"
                declare -A STARTUP_SELECTED_ROOM_SEEN=()
                for room in "${COOKED_STARTUP_ROOMS[@]}"; do
                    STARTUP_SELECTED_ROOM_SEEN["$room"]=1
                done
                for room in "${FULL_STARTUP_ROOMS[@]}"; do
                    if [[ ! "$room" =~ ^[0-9]+$ ]]; then
                        echo "Invalid full authentic startup room ID: $room" >&2
                        exit 1
                    fi
                    room=$((10#$room))
                    if (( room > 255 )) || [[ -z "${STARTUP_SELECTED_ROOM_SEEN[$room]:-}" ]]; then
                        echo "Full authentic startup room must be selected: $room" >&2
                        exit 1
                    fi
                    if [[ -n "${STARTUP_FULL_ROOM_SEEN[$room]:-}" ]]; then
                        echo "Duplicate full authentic startup room ID: $room" >&2
                        exit 1
                    fi
                    STARTUP_FULL_ROOM_SEEN["$room"]=1
                done
                unset STARTUP_SELECTED_ROOM_SEEN
            fi
            COOKED_STARTUP_GLOBAL_ARGS=()
            if [[ -n "${SAME_SCUMM_STARTUP_GLOBAL_SCRIPTS:-}" ]]; then
                IFS=',' read -r -a STARTUP_GLOBAL_SCRIPTS <<< "${SAME_SCUMM_STARTUP_GLOBAL_SCRIPTS}"
                COOKED_STARTUP_GLOBAL_ARGS+=(--global-scripts "${STARTUP_GLOBAL_SCRIPTS[@]}")
            fi
            "$PYTHON" tools/cook_scumm_v5_rooms.py \
                --archive "$M23A_SOURCE" \
                --profile "$SAME_FATE_PROFILE" \
                --rooms "${COOKED_STARTUP_ROOMS[@]}" \
                "${COOKED_STARTUP_GLOBAL_ARGS[@]}" \
                --executable \
                $([[ "${SAME_BUILD_SCUMM_ROOM_VISUAL:-0}" == "1" ]] && echo --visuals "${COOKED_STARTUP_ROOMS[@]}") \
                --output-dir "$M25A_BUILD/room42"
            ROOM_MANIFESTS+=(--manifest "$M25A_BUILD/room42/manifest.json")
        fi
    else
        ROOM_MANIFESTS=(--manifest "$M23A_BUILD/authentic/manifest.json")
        ROOM_BINARY_DIR="$M23A_BUILD/segments"
    fi
    if [[ "$M25A_CONTENT_PROFILE" == "1" ]]; then
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
            # Phase 6 is a deliberate mid-game fixture root. The cooker emits
            # a separately identified synthetic wrapper for global 144 and
            # preserves the unchanged authored body as script-144.source.scrp;
            # this is fixture setup, not an authentic cold-start path.
            ROOM49_GLOBAL_ARGS+=(--prepend-global-script 144 18)
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
    if [[ "$M25A_CONTENT_PROFILE" != "1" ]]; then
        "$PYTHON" tools/build_m23a_lifecycle_rooms.py \
            --output-dir "$M23A_BUILD/lifecycle"
    fi
    fi
    ROOM_GENERATOR_ARGS=()
    if [[ -n "${SAME_SCUMM_APPEND_GLOBAL_SCRIPTS:-}" ]]; then
        IFS=',' read -r -a APPEND_GLOBAL_SCRIPTS <<< "${SAME_SCUMM_APPEND_GLOBAL_SCRIPTS}"
        for global_script in "${APPEND_GLOBAL_SCRIPTS[@]}"; do
            ROOM_GENERATOR_ARGS+=(--append-global-script "$global_script")
        done
    fi
    if [[ -n "${SAME_SCUMM_APPEND_EXECUTABLE_LOCALS:-}" ]]; then
        IFS=',' read -r -a APPEND_EXECUTABLE_LOCALS <<< "${SAME_SCUMM_APPEND_EXECUTABLE_LOCALS}"
        for local_script in "${APPEND_EXECUTABLE_LOCALS[@]}"; do
            ROOM_GENERATOR_ARGS+=(--append-executable-local "$local_script")
        done
    fi
    if [[ -n "${SAME_SCUMM_APPEND_EXECUTABLE_LOCAL_OBJECTS:-}" ]]; then
        IFS=',' read -r -a APPEND_EXECUTABLE_LOCAL_OBJECTS <<< "${SAME_SCUMM_APPEND_EXECUTABLE_LOCAL_OBJECTS}"
        for local_object in "${APPEND_EXECUTABLE_LOCAL_OBJECTS[@]}"; do
            ROOM_GENERATOR_ARGS+=(--append-executable-local-object "$local_object")
        done
    fi
    if [[ -n "${SAME_SCUMM_EXTRA_EXECUTABLE_LOCALS:-}" ]]; then
        IFS=',' read -r -a EXTRA_EXECUTABLE_LOCALS <<< "${SAME_SCUMM_EXTRA_EXECUTABLE_LOCALS}"
        for local_script in "${EXTRA_EXECUTABLE_LOCALS[@]}"; do
            ROOM_GENERATOR_ARGS+=(--executable-local "$local_script")
        done
    fi
    if [[ -n "${SAME_SCUMM_APPEND_LATE_GLOBAL_SCRIPTS:-}" ]]; then
        IFS=',' read -r -a APPEND_LATE_GLOBAL_SCRIPTS <<< "${SAME_SCUMM_APPEND_LATE_GLOBAL_SCRIPTS}"
        for global_script in "${APPEND_LATE_GLOBAL_SCRIPTS[@]}"; do
            ROOM_GENERATOR_ARGS+=(--append-late-global-script "$global_script")
        done
    fi
    if [[ -n "${SAME_SCUMM_APPEND_FINAL_GLOBAL_SCRIPTS:-}" ]]; then
        IFS=',' read -r -a APPEND_FINAL_GLOBAL_SCRIPTS <<< "${SAME_SCUMM_APPEND_FINAL_GLOBAL_SCRIPTS}"
        for global_script in "${APPEND_FINAL_GLOBAL_SCRIPTS[@]}"; do
            ROOM_GENERATOR_ARGS+=(--append-final-global-script "$global_script")
        done
    fi
    if [[ -n "${SAME_SCUMM_APPEND_TERMINAL_GLOBAL_SCRIPTS:-}" ]]; then
        IFS=',' read -r -a APPEND_TERMINAL_GLOBAL_SCRIPTS <<< "${SAME_SCUMM_APPEND_TERMINAL_GLOBAL_SCRIPTS}"
        for global_script in "${APPEND_TERMINAL_GLOBAL_SCRIPTS[@]}"; do
            ROOM_GENERATOR_ARGS+=(--append-terminal-global-script "$global_script")
        done
    fi
    if [[ -n "${SAME_SCUMM_APPEND_POST_TERMINAL_GLOBAL_SCRIPTS:-}" ]]; then
        IFS=',' read -r -a APPEND_POST_TERMINAL_GLOBAL_SCRIPTS <<< "${SAME_SCUMM_APPEND_POST_TERMINAL_GLOBAL_SCRIPTS}"
        for global_script in "${APPEND_POST_TERMINAL_GLOBAL_SCRIPTS[@]}"; do
            ROOM_GENERATOR_ARGS+=(--append-post-terminal-global-script "$global_script")
        done
    fi
    if [[ -n "${SAME_SCUMM_APPEND_LAST_GLOBAL_SCRIPTS:-}" ]]; then
        IFS=',' read -r -a APPEND_LAST_GLOBAL_SCRIPTS <<< "${SAME_SCUMM_APPEND_LAST_GLOBAL_SCRIPTS}"
        for global_script in "${APPEND_LAST_GLOBAL_SCRIPTS[@]}"; do
            ROOM_GENERATOR_ARGS+=(--append-last-global-script "$global_script")
        done
    fi
    if [[ -n "${SAME_SCUMM_APPEND_LATE_ROOM_ENTRY_EXITS:-}" ]]; then
        IFS=',' read -r -a APPEND_LATE_ROOM_ENTRY_EXITS <<< "${SAME_SCUMM_APPEND_LATE_ROOM_ENTRY_EXITS}"
        for room_number in "${APPEND_LATE_ROOM_ENTRY_EXITS[@]}"; do
            ROOM_GENERATOR_ARGS+=(--append-late-room-entry-exit "$room_number")
        done
    fi
    if [[ -n "${SAME_SCUMM_APPEND_ROOM_ENTRY_EXITS:-}" ]]; then
        IFS=',' read -r -a APPEND_ROOM_ENTRY_EXITS <<< "${SAME_SCUMM_APPEND_ROOM_ENTRY_EXITS}"
        for room_number in "${APPEND_ROOM_ENTRY_EXITS[@]}"; do
            ROOM_GENERATOR_ARGS+=(--append-room-entry-exit "$room_number")
        done
    fi
    if [[ -n "${SAME_SCUMM_APPEND_LATE_EXECUTABLE_LOCALS:-}" ]]; then
        IFS=',' read -r -a APPEND_LATE_EXECUTABLE_LOCALS <<< "${SAME_SCUMM_APPEND_LATE_EXECUTABLE_LOCALS}"
        for local_script in "${APPEND_LATE_EXECUTABLE_LOCALS[@]}"; do
            ROOM_GENERATOR_ARGS+=(--append-late-executable-local "$local_script")
        done
    fi
    if [[ -n "${SAME_SCUMM_APPEND_FINAL_EXECUTABLE_LOCALS:-}" ]]; then
        IFS=',' read -r -a APPEND_FINAL_EXECUTABLE_LOCALS <<< "${SAME_SCUMM_APPEND_FINAL_EXECUTABLE_LOCALS}"
        for local_script in "${APPEND_FINAL_EXECUTABLE_LOCALS[@]}"; do
            ROOM_GENERATOR_ARGS+=(--append-final-executable-local "$local_script")
        done
    fi
    if [[ -n "${SAME_SCUMM_APPEND_TERMINAL_EXECUTABLE_LOCALS:-}" ]]; then
        IFS=',' read -r -a APPEND_TERMINAL_EXECUTABLE_LOCALS <<< "${SAME_SCUMM_APPEND_TERMINAL_EXECUTABLE_LOCALS}"
        for local_script in "${APPEND_TERMINAL_EXECUTABLE_LOCALS[@]}"; do
            ROOM_GENERATOR_ARGS+=(--append-terminal-executable-local "$local_script")
        done
    fi
    if [[ -n "${SAME_SCUMM_APPEND_POST_TERMINAL_EXECUTABLE_LOCALS:-}" ]]; then
        IFS=',' read -r -a APPEND_POST_TERMINAL_EXECUTABLE_LOCALS <<< "${SAME_SCUMM_APPEND_POST_TERMINAL_EXECUTABLE_LOCALS}"
        for local_script in "${APPEND_POST_TERMINAL_EXECUTABLE_LOCALS[@]}"; do
            ROOM_GENERATOR_ARGS+=(--append-post-terminal-executable-local "$local_script")
        done
    fi
    if [[ -n "${SAME_SCUMM_APPEND_LAST_EXECUTABLE_LOCALS:-}" ]]; then
        IFS=',' read -r -a APPEND_LAST_EXECUTABLE_LOCALS <<< "${SAME_SCUMM_APPEND_LAST_EXECUTABLE_LOCALS}"
        for local_script in "${APPEND_LAST_EXECUTABLE_LOCALS[@]}"; do
            ROOM_GENERATOR_ARGS+=(--append-last-executable-local "$local_script")
        done
    fi
    if [[ -n "${SAME_SCUMM_APPEND_ULTIMATE_EXECUTABLE_LOCALS:-}" ]]; then
        IFS=',' read -r -a APPEND_ULTIMATE_EXECUTABLE_LOCALS <<< "${SAME_SCUMM_APPEND_ULTIMATE_EXECUTABLE_LOCALS}"
        for local_script in "${APPEND_ULTIMATE_EXECUTABLE_LOCALS[@]}"; do
            ROOM_GENERATOR_ARGS+=(--append-ultimate-executable-local "$local_script")
        done
    fi
    if [[ -n "${SAME_SCUMM_APPEND_TERMINAL_EXECUTABLE_LOCAL_OBJECTS:-}" ]]; then
        IFS=',' read -r -a APPEND_TERMINAL_EXECUTABLE_LOCAL_OBJECTS <<< "${SAME_SCUMM_APPEND_TERMINAL_EXECUTABLE_LOCAL_OBJECTS}"
        for local_object in "${APPEND_TERMINAL_EXECUTABLE_LOCAL_OBJECTS[@]}"; do
            ROOM_GENERATOR_ARGS+=(--append-terminal-executable-local-object "$local_object")
        done
    fi
    if [[ -n "${SAME_SCUMM_APPEND_LAST_EXECUTABLE_LOCAL_OBJECTS:-}" ]]; then
        IFS=',' read -r -a APPEND_LAST_EXECUTABLE_LOCAL_OBJECTS <<< "${SAME_SCUMM_APPEND_LAST_EXECUTABLE_LOCAL_OBJECTS}"
        for local_object in "${APPEND_LAST_EXECUTABLE_LOCAL_OBJECTS[@]}"; do
            ROOM_GENERATOR_ARGS+=(--append-last-executable-local-object "$local_object")
        done
    fi
    if [[ "$M25A_CONTENT_PROFILE" == "1" ]]; then
        if [[ "${SAME_BUILD_SCUMM_SCENARIO_FIXTURE:-0}" == "1" || \
              "${SAME_BUILD_SCUMM_AUTHENTIC_STARTUP:-0}" == "1" ]]; then
            if [[ "$M25A_PROFILE_CASE" == "fishnet" ]]; then
                ROOM_GENERATOR_ARGS+=(--executable-local-room 49 --executable-local-object 49:595 --far-programs --far-validator-output runtime/snes/generated/scumm_v5_room_validator_far.inc.pasm)
            elif [[ "$M25A_PROFILE_CASE" == "balloon" ]]; then
                ROOM_GENERATOR_ARGS+=(--executable-local-room 49 --executable-local-object 49:593 --far-programs --far-validator-output runtime/snes/generated/scumm_v5_room_validator_far.inc.pasm)
            elif [[ "$M25A_PROFILE_CASE" == "salvage" ]]; then
                ROOM_GENERATOR_ARGS+=(--executable-local-room 49 --executable-local-object 49:592 --far-programs --far-validator-output runtime/snes/generated/scumm_v5_room_validator_far.inc.pasm)
            elif [[ "$M25A_PROFILE_CASE" == "startobject-replacement" || "$M25A_PROFILE_CASE" == "startobject-long-replacement" ]]; then
                ROOM_GENERATOR_ARGS+=(--executable-local-room 49 --executable-local-object 49:100 --far-programs --far-validator-output runtime/snes/generated/scumm_v5_room_validator_far.inc.pasm)
            elif [[ "$M25A_PROFILE_CASE" == "global-room-continuation" ]]; then
                ROOM_GENERATOR_ARGS+=(--entry-only-room 49 --entry-only-room 50 --far-programs --far-validator-output runtime/snes/generated/scumm_v5_room_validator_far.inc.pasm)
            elif [[ "$M25A_PROFILE_CASE" == "local-room-continuation" ]]; then
                ROOM_GENERATOR_ARGS+=(--entry-only-room 49 --entry-only-room 50 --executable-local 49:200 --far-programs --far-validator-output runtime/snes/generated/scumm_v5_room_validator_far.inc.pasm)
            elif [[ "$M25A_PROFILE_CASE" == "pending-room-request" ]]; then
                ROOM_GENERATOR_ARGS+=(--entry-only-room 49 --entry-only-room 50 --entry-only-room 51)
                if [[ "${SAME_BUILD_M24RB:-0}" == "1" || "${SAME_BUILD_SCUMM_CONTROLLER_CONFORMANCE:-0}" == "1" ]]; then
                    ROOM_GENERATOR_ARGS+=(--far-programs --far-validator-output runtime/snes/generated/scumm_v5_room_validator_far.inc.pasm)
                fi
            elif [[ "$M25A_PROFILE_CASE" == "startup42" || "$M25A_PROFILE_CASE" == "room55" ]]; then
                # Startup traverses source-authentic room entries, including
                # room 4 after room68's room0 handoff. Its authored actor-follow
                # operation then enters room5; retain both authentic entry/exit
                # pairs while adding locals only as execution proves them
                # reachable, rather than bloating bank0 with whole directories.
                for room_number in "${COOKED_STARTUP_BASE_ROOMS[@]}"; do
                    if [[ -n "${STARTUP_FULL_ROOM_SEEN[$room_number]:-}" ]]; then
                        ROOM_GENERATOR_ARGS+=(--executable-local-room "$room_number")
                    else
                        ROOM_GENERATOR_ARGS+=(--entry-only-room "$room_number")
                    fi
                done
                if [[ -z "${STARTUP_FULL_ROOM_SEEN[68]:-}" &&
                      " ${COOKED_STARTUP_ROOMS[*]} " == *" 68 "* ]]; then
                    ROOM_GENERATOR_ARGS+=(--executable-local 68:200 --executable-local 68:201)
                fi
                if [[ " ${COOKED_STARTUP_ROOMS[*]} " == *" 42 "* ]]; then
                ROOM_GENERATOR_ARGS+=(
                                      # Retain the complete room-42 local-script cone.  The
                                      # switch/hoist sequence crosses several authored local
                                      # continuations (including 201, 202, 207, and 212); partial
                                      # retention turns valid source control flow into a no-op.
                                      --executable-local 42:200 --executable-local 42:201
                                      --executable-local 42:208
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
                                      )
                fi
                ROOM_GENERATOR_ARGS+=(--far-programs --far-validator-output runtime/snes/generated/scumm_v5_room_validator_far.inc.pasm)
                if [[ " ${COOKED_STARTUP_BASE_ROOMS[*]} " == *" 82 "* ]]; then
                    ROOM_GENERATOR_ARGS+=(--executable-local 82:200 --executable-local 82:201 --executable-local 82:202
                                          --executable-local 82:203 --executable-local 82:204 --executable-local 82:205)
                fi
                # Extra authentic startup-path rooms are resource records,
                # not permission to allocate every dormant LSCR or shift the
                # established executable map. Their entry/exit pairs and
                # individually reached locals are appended after existing
                # identities through the explicit append selections below.
                if [[ -n "${SAME_SCUMM_AUTHENTIC_STARTUP_EXTRA_ROOMS:-}" ]]; then
                    IFS=',' read -r -a EXTRA_STARTUP_ROOMS <<< \
                        "${SAME_SCUMM_AUTHENTIC_STARTUP_EXTRA_ROOMS}"
                    for room_number in "${EXTRA_STARTUP_ROOMS[@]}"; do
                        room_number=$((10#$room_number))
                        ROOM_GENERATOR_ARGS+=(--entry-only-room "$room_number"
                                              --append-terminal-room-entry-exit "$room_number")
                    done
                fi
                if [[ -n "${SAME_SCUMM_AUTHENTIC_STARTUP_FINAL_ROOMS:-}" ]]; then
                    IFS=',' read -r -a FINAL_STARTUP_ROOMS <<< \
                        "${SAME_SCUMM_AUTHENTIC_STARTUP_FINAL_ROOMS}"
                    for room_number in "${FINAL_STARTUP_ROOMS[@]}"; do
                        room_number=$((10#$room_number))
                        ROOM_GENERATOR_ARGS+=(--entry-only-room "$room_number"
                                              --append-last-room-entry-exit "$room_number")
                    done
                fi
                # Scenario overlays are source-backed prerequisites applied by
                # the engine at the accepted sentence boundary.  Keep the
                # controller startup profile on the same path as the proven
                # locker fixture; never materialize these values by writing
                # interpreter state from the validator.
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
                if [[ "${SAME_BUILD_SCUMM_CONTROLLER_FIXTURE:-0}" != "1" ]]; then
                    # The hoist/full-cone profile retains the auxiliary
                    # authored continuations.  The controller scene's
                    # accepted locker cone does not start local 204/207;
                    # omitting those unrelated ambient continuations prevents
                    # their independent unreachable-actor wait from becoming
                    # a false input-readiness gate.
                    if [[ " ${COOKED_STARTUP_ROOMS[*]} " == *" 42 "* ]]; then
                        ROOM_GENERATOR_ARGS+=(--executable-local 42:204 --executable-local 42:207)
                    fi
                fi
            elif [[ "$M25A_PROFILE_CASE" == "room55-movement" ]]; then
                # Standalone copyright-free movement fixture: keep its one
                # synthetic room 49 record and local script only.  Do not
                # merge the Fate startup closure, which also contains room 49
                # and can make record selection depend on manifest order.
                ROOM_GENERATOR_ARGS+=(--executable-local-room 49 --far-programs --far-validator-output runtime/snes/generated/scumm_v5_room_validator_far.inc.pasm)
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
            if [[ "${SAME_BUILD_SCUMM_ROOM_SERVICE_FAR:-0}" == "1" || "${SAME_BUILD_M24RB:-0}" == "1" || "${SAME_BUILD_SCUMM_PHASE6HB:-0}" == "1" ]]; then
                ROOM_GENERATOR_ARGS+=(--far-programs --far-validator-output runtime/snes/generated/scumm_v5_room_validator_far.inc.pasm)
            fi
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
            if [[ "${SAME_BUILD_SCUMM_ROOM_SERVICE_FAR:-0}" == "1" || "${SAME_BUILD_M24RB:-0}" == "1" || "${SAME_BUILD_SCUMM_PHASE6HB:-0}" == "1" ]]; then
                ROOM_GENERATOR_ARGS+=(--far-validator-output runtime/snes/generated/scumm_v5_room_validator_far.inc.pasm)
            fi
        fi
    fi
    if [[ "$M25A_CONTENT_PROFILE" != "1" &&
          "${SAME_BUILD_SCUMM_M23C:-0}" != "1" &&
          "${SAME_BUILD_SCUMM_DYNAMIC_PROGRAM_RESIDENCY:-0}" != "1" ]]; then
        ROOM_MANIFESTS+=(--manifest "$M23A_BUILD/lifecycle/manifest.json")
    fi
    fi
    if [[ -n "${SAME_SCUMM_OMIT_EXECUTABLE_LOCALS:-}" ]]; then
        IFS=',' read -r -a OMIT_EXECUTABLE_LOCALS <<< "${SAME_SCUMM_OMIT_EXECUTABLE_LOCALS}"
        declare -A OMIT_LOCAL_SET=() OMIT_LOCAL_SEEN=()
        for local_script in "${OMIT_EXECUTABLE_LOCALS[@]}"; do
            if [[ ! "$local_script" =~ ^[0-9]+:[0-9]+$ || -n "${OMIT_LOCAL_SET[$local_script]:-}" ]]; then
                echo "Invalid or duplicate omitted executable local: $local_script" >&2
                exit 1
            fi
            OMIT_LOCAL_SET[$local_script]=1
        done
        FILTERED_ROOM_GENERATOR_ARGS=()
        for ((arg_index = 0; arg_index < ${#ROOM_GENERATOR_ARGS[@]}; arg_index++)); do
            if [[ "${ROOM_GENERATOR_ARGS[$arg_index]}" == "--executable-local" &&
                  $((arg_index + 1)) -lt ${#ROOM_GENERATOR_ARGS[@]} ]]; then
                local_script="${ROOM_GENERATOR_ARGS[$((arg_index + 1))]}"
                if [[ -n "${OMIT_LOCAL_SET[$local_script]:-}" ]]; then
                    OMIT_LOCAL_SEEN[$local_script]=1
                    arg_index=$((arg_index + 1))
                    continue
                fi
            fi
            FILTERED_ROOM_GENERATOR_ARGS+=("${ROOM_GENERATOR_ARGS[$arg_index]}")
        done
        for local_script in "${OMIT_EXECUTABLE_LOCALS[@]}"; do
            if [[ -z "${OMIT_LOCAL_SEEN[$local_script]:-}" ]]; then
                echo "Omitted executable local was not selected by this build: $local_script" >&2
                exit 1
            fi
        done
        ROOM_GENERATOR_ARGS=("${FILTERED_ROOM_GENERATOR_ARGS[@]}")
    fi
    ROOM_GENERATOR_REPORT="$M23A_BUILD/cooked-rooms.json"
    ROOM_GENERATOR_ARGS+=(--report "$ROOM_GENERATOR_REPORT")
    if [[ "${SAME_SNES_CARRIER:-lorom}" == "sa1_bwram" ]]; then
        ROOM_GENERATOR_ARGS+=(--sa1-rom-bank-aliases)
    fi
    # The mode-3 surface backend owns bank 15.  Keep generated room payloads
    # out of every fixed code bank instead of allowing a later include to
    # overwrite a cooked record silently.
    if [[ "${SAME_SNES_VIDEO_BACKEND:-legacy_backdrop}" == "mode3_surface" ]]; then
        # Fixed presentation/data sections occupy these banks in the current
        # SA-1 mode-3 layout: carrier, backend, actor/room visual code,
        # overlay, and charset.
        ROOM_GENERATOR_ARGS+=(--reserved-bank 14 --reserved-bank 15
                              --reserved-bank 20 --reserved-bank 21
                              --reserved-bank 22 --reserved-bank 23
                              --reserved-bank 24)
    fi
    if [[ "${SAME_BUILD_M24RB:-0}" == "1" || "${SAME_BUILD_SCUMM_ROOM_SERVICE_FAR:-0}" == "1" || "${SAME_BUILD_SCUMM_CONTROLLER_CONFORMANCE:-0}" == "1" ]]; then
        # The far room-service closure is fixed in banks 9 and 83 for both
        # M24R-B production profiles and controller-conformance builds.
        # Keep generated room tables/helpers out of both banks even when the
        # selected room manifest is empty; otherwise the name/lookup helpers
        # can collide with the fixed bank-9 service entry.
        ROOM_GENERATOR_ARGS+=(--reserved-bank 9 --reserved-bank 83)
    fi
    ROOM_GENERATOR_ARGS+=(--relative-binary-paths)
    if [[ -n "${SAME_SCUMM_ROOM_DATA_FIRST_BANK:-}" ]]; then
        ROOM_GENERATOR_ARGS+=(--first-bank "$SAME_SCUMM_ROOM_DATA_FIRST_BANK")
    fi
    if [[ "${SAME_BUILD_SCUMM_DYNAMIC_PROGRAM_RESIDENCY:-0}" == "1" ]]; then
        ROOM_GENERATOR_ARGS+=(--far-programs --dynamic-program-residency
            --far-validator-output runtime/snes/generated/scumm_v5_room_validator_far.inc.pasm
            --native-directory-output "$M23A_BUILD/scumm_v5_native_program_directory.json"
            --native-directory-include "$M23A_BUILD/scumm_v5_native_program_directory.inc.pasm"
            --reserved-bank 9 --reserved-bank 83)
    elif [[ "${SAME_SCUMM_FAR_PROGRAMS:-0}" == "1" ]]; then
        # Keep the legacy global selector ABI while placing selected source
        # bodies in the existing banked-ROM fetch path. This is useful for
        # larger static-control corpora that exceed the bank-0 inline area.
        ROOM_GENERATOR_ARGS+=(--far-programs)
    fi
    if [[ "${SAME_BUILD_SCUMM_MSU1_PROGRAMS:-0}" == "1" ]]; then
        MSU_PROGRAM_STORAGE_DIR="${SAME_SCUMM_MSU1_PROGRAM_STORAGE_DIR:-$M23A_BUILD/msu-program-storage}"
        mkdir -p "$MSU_PROGRAM_STORAGE_DIR"
        ROOM_GENERATOR_ARGS+=(--msu1-program-storage-dir "$MSU_PROGRAM_STORAGE_DIR"
            --msu1-program-directory-include runtime/snes/generated/scumm_v5_msu_programs.inc.pasm
            --msu1-program-directory-bank 10
            --msu1-program-page-directory-bank 12
            --reserved-bank 10 --reserved-bank 11 --reserved-bank 12)
        if [[ "${SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES:-0}" == "1" ]]; then
            ROOM_GENERATOR_ARGS+=(--msu1-live-room-resources)
            if [[ -n "${SAME_SCUMM_WHOLE_SOURCE_MANIFEST:-}" ]]; then
                ROOM_GENERATOR_ARGS+=(--msu1-include-source-room-records)
            fi
        fi
        if [[ -n "${SAME_SCUMM_MSU1_PREFIX_PACKAGE:-}" ||
              -n "${SAME_SCUMM_MSU1_PREFIX_SECTION:-}" ||
              "${SAME_SCUMM_MSU1_PREFIX_ALL_SECTIONS:-0}" == "1" ]]; then
            if [[ -z "${SAME_SCUMM_MSU1_PREFIX_PACKAGE:-}" ||
                  ! -f "${SAME_SCUMM_MSU1_PREFIX_PACKAGE}" ]]; then
                echo "MSU ProgramUnit prefix requires an existing SAMEPKG source and section name" >&2
                exit 1
            fi
            ROOM_GENERATOR_ARGS+=(--msu1-program-prefix-package "$SAME_SCUMM_MSU1_PREFIX_PACKAGE")
            if [[ "${SAME_SCUMM_MSU1_PREFIX_ALL_SECTIONS:-0}" == "1" ]]; then
                ROOM_GENERATOR_ARGS+=(--msu1-program-prefix-all-sections)
            elif [[ -n "${SAME_SCUMM_MSU1_PREFIX_SECTION:-}" ]]; then
                ROOM_GENERATOR_ARGS+=(--msu1-program-prefix-section "$SAME_SCUMM_MSU1_PREFIX_SECTION")
            else
                echo "MSU ProgramUnit prefix selection is missing" >&2
                exit 1
            fi
        fi
    fi
    if [[ -n "${SAME_SCUMM_WHOLE_SOURCE_MANIFEST:-}" ]]; then
        ROOM_GENERATOR_ARGS+=(--pack-source-tables --banked-room-directory-data
            --backend-directory-output "$M23A_BUILD/backend_program_directory.json")
        if [[ "${SAME_BUILD_SCUMM_MSU1_PROGRAMS:-0}" != "1" ]]; then
            ROOM_GENERATOR_ARGS+=(--share-room-program-bodies
                --share-room-directory-prefixes)
        fi
    elif [[ "${SAME_SCUMM_PACK_SOURCE_TABLES:-0}" == "1" ]]; then
        # Selected source-backed controls can contain many room metadata
        # tables too. Pack their immutable tables rather than spending one
        # entire 32 KiB ROM page on each small field. Dynamic builds also use
        # the banked room-directory representation required by their
        # canonical ProgramUnit resolver.
        ROOM_GENERATOR_ARGS+=(--pack-source-tables)
        if [[ "${SAME_BUILD_SCUMM_DYNAMIC_PROGRAM_RESIDENCY:-0}" == "1" ]]; then
            ROOM_GENERATOR_ARGS+=(--banked-room-directory-data)
        fi
    fi
    "$PYTHON" tools/generate_snes_cooked_rooms.py \
        "${ROOM_MANIFESTS[@]}" \
        --output runtime/snes/generated/scumm_v5_rooms.inc.pasm \
        --data-output runtime/snes/generated/scumm_v5_room_data.inc.pasm \
        --binary-dir "$ROOM_BINARY_DIR" \
        "${ROOM_GENERATOR_ARGS[@]}"
    ROOM_TABLES_GENERATED=1
    if [[ "${SAME_BUILD_SCUMM_ROOM_VISUAL:-0}" == "1" ]]; then
        if [[ "${SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES:-0}" == "1" ]]; then
            # The canonical visual payload is in the checked SC5VIS package
            # section. Keep only zero-count compile-time symbols for dormant
            # ROM visual routines; no descriptor or pixel payload is emitted.
            printf '%s\n' \
                '; Live-room mode: no ROM visual descriptors or pixel payloads exist.' \
                'SCUMM_V5_ROOM_VISUAL_COUNT = $00' \
                'SCUMM_V5_INITIAL_VISUAL_ROOM = $00' \
                'SCUMM_V5_ROOM_VISUAL_DESCRIPTOR_MAGIC = $5652' \
                'SCUMM_V5_ROOM_VISUAL_DESCRIPTOR_VERSION = $01' \
                'SCUMM_V5_ROOM_VISUAL_FIRST_DATA_BANK = $00' \
                'SCUMM_V5_ROOM_VISUAL_LAST_DATA_BANK = $00' \
                'SCUMM_V5_ROOM_VISUAL_DIRECTORY = $000000' \
                > runtime/snes/generated/scumm_v5_room_visuals.inc.pasm
        else
            ROOM_VISUAL_MANIFEST="${SAME_SCUMM_ROOM_VISUAL_MANIFEST:-$M23A_BUILD/authentic/manifest.json}"
            if [[ -n "${SAME_SCUMM_ROOM_VISUAL_FIRST_BANK:-}" ]]; then
                ROOM_VISUAL_FIRST_BANK="$SAME_SCUMM_ROOM_VISUAL_FIRST_BANK"
            else
                ROOM_VISUAL_FIRST_BANK="$(( $("$PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1]))["last_bank"])' "$ROOM_GENERATOR_REPORT") + 1 ))"
            fi
            if [[ "${SAME_SCUMM_REUSE_COOKED_ROOM_VISUALS:-0}" == "1" ]]; then
                test -s runtime/snes/generated/scumm_v5_room_visuals.inc.pasm
                echo "Reusing existing cooked room-visual delivery"
            else
                "$PYTHON" tools/generate_snes_room_visuals.py \
                    --manifest "$ROOM_VISUAL_MANIFEST" \
                    --output runtime/snes/generated/scumm_v5_room_visuals.inc.pasm \
                    --binary-dir "$M23A_BUILD/visual-segments" \
                    --report "${SAME_SNES_OUTPUT:-build/same-engine-host.sfc}.room-visuals.json" \
                    --first-bank "$ROOM_VISUAL_FIRST_BANK" \
                    ${SAME_SCUMM_ROOM_VISUAL_ROOMS:+$(for room in ${SAME_SCUMM_ROOM_VISUAL_ROOMS//,/ }; do printf -- '--room %s ' "$room"; done)}
            fi
        fi
    fi
    if [[ "${SAME_BUILD_SCUMM_CONTROLLER_FIXTURE:-0}" == "1" ]]; then
        "$PYTHON" tools/generate_snes_scumm_actor_sprite.py \
            --archive "${SAME_FATE_ARCHIVE:?Set SAME_FATE_ARCHIVE to a user-supplied archive}" \
            --profile "${SAME_SNES_PROFILE:-examples/profiles/templates/fate_of_atlantis_demo.json}" \
            --costume 2 \
            --facing "${SAME_SCUMM_ACTOR_SPRITE_FACING:-90}" \
            --output runtime/snes/generated/scumm_v5_actor_sprite.inc.pasm \
            --bank "${SAME_SCUMM_ACTOR_SPRITE_BANK:-118}"
        "$PYTHON" tools/generate_snes_scumm_object_sprite.py \
            --archive "${SAME_FATE_ARCHIVE:?Set SAME_FATE_ARCHIVE to a user-supplied archive}" \
            --profile "${SAME_SNES_PROFILE:-examples/profiles/templates/fate_of_atlantis_demo.json}" \
            --room 42 --object 490 \
            --output runtime/snes/generated/scumm_v5_object_sprite.inc.pasm \
            --bank "${SAME_SCUMM_OBJECT_SPRITE_BANK:-119}"
    fi
fi
if [[ "$ROOM_TABLES_GENERATED" != "1" ]]; then
    # SCUMM engine builds without a selected room/content profile still
    # include the generated room lookup and validator symbols. Generate their
    # deterministic empty form instead of inheriting ignored files from a
    # previous profile build.
    EMPTY_ROOM_ARGS=()
    if [[ "${SAME_BUILD_M24RB:-0}" == "1" ]]; then
        EMPTY_ROOM_ARGS+=(--far-programs
            --far-validator-output runtime/snes/generated/scumm_v5_room_validator_far.inc.pasm)
    fi
    "$PYTHON" tools/generate_snes_cooked_rooms.py \
        --manifest examples/resources/scumm_v5/empty_cooked_rooms.json \
        --output runtime/snes/generated/scumm_v5_rooms.inc.pasm \
        --data-output runtime/snes/generated/scumm_v5_room_data.inc.pasm \
        --binary-dir build/empty-scumm-rooms/segments \
        --report build/empty-scumm-rooms/report.json \
        "${EMPTY_ROOM_ARGS[@]}"
fi
if [[ "${SAME_SNES_ENGINE:-demo}" == "winston_io" ]]; then
    if [[ -z "${SAME_MSU1_PACKAGE:-}" || -z "${SAME_MSU1_READ_CASES:-}" ]]; then
        echo "winston_io requires SAME_MSU1_PACKAGE and SAME_MSU1_READ_CASES" >&2
        exit 1
    fi
    if [[ ! -f "$SAME_MSU1_PACKAGE" || ! -f "$SAME_MSU1_READ_CASES" ]]; then
        echo "MSU package or read-case manifest is missing" >&2
        exit 1
    fi
    "$PYTHON" tools/generate_snes_msu1_directory.py "$SAME_MSU1_PACKAGE" \
        --include runtime/snes/generated/msu1_package.inc.pasm \
        --manifest "${SAME_SNES_OUTPUT:-build/winston_io.sfc}.msu1-directory.json" \
        --read-cases "$SAME_MSU1_READ_CASES" \
        --cases-include runtime/snes/generated/msu1_read_cases.inc.pasm
    ENGINE_SELECTION_ARGS+=(--msu1-storage)
    if [[ "${SAME_MSU1_TEST_FORCE_BUSY:-0}" == "1" ]]; then
        ENGINE_SELECTION_ARGS+=(--msu1-test-force-busy)
    fi
    SAME_MSU1_PCM_DIR="${SAME_MSU1_PCM_DIR:-$(dirname "$SAME_MSU1_PACKAGE")}"

    SAME_MSU1_STEM="${SAME_SNES_OUTPUT##*/}"
    SAME_MSU1_STEM="${SAME_MSU1_STEM%.sfc}"
    SAME_MSU1_DEST_DIR="$(dirname "$SAME_SNES_OUTPUT")"
    mkdir -p "$SAME_MSU1_DEST_DIR"
    SAME_MSU1_PACKAGE_DEST="$SAME_MSU1_DEST_DIR/$SAME_MSU1_STEM.msu"
    if [[ -e "$SAME_MSU1_PACKAGE_DEST" ]]; then
        if ! cmp -s "$SAME_MSU1_PACKAGE" "$SAME_MSU1_PACKAGE_DEST"; then
            echo "Refusing to overwrite non-identical MSU package: $SAME_MSU1_PACKAGE_DEST" >&2
            exit 1
        fi
    else
        cp "$SAME_MSU1_PACKAGE" "$SAME_MSU1_PACKAGE_DEST"
    fi
    for track in 1 2 101 102 103 104; do
        SAME_MSU1_PCM_SOURCE="$SAME_MSU1_PCM_DIR/winston_io-$track.pcm"
        SAME_MSU1_PCM_DEST="$SAME_MSU1_DEST_DIR/$SAME_MSU1_STEM-$track.pcm"
        if [[ ! -f "$SAME_MSU1_PCM_SOURCE" ]]; then
            echo "Missing required diagnostic PCM sidecar: $SAME_MSU1_PCM_SOURCE" >&2
            exit 1
        fi
        if [[ -e "$SAME_MSU1_PCM_DEST" ]]; then
            if ! cmp -s "$SAME_MSU1_PCM_SOURCE" "$SAME_MSU1_PCM_DEST"; then
                echo "Refusing to overwrite non-identical PCM sidecar: $SAME_MSU1_PCM_DEST" >&2
                exit 1
            fi
        else
            cp "$SAME_MSU1_PCM_SOURCE" "$SAME_MSU1_PCM_DEST"
        fi
    done
elif [[ "${SAME_BUILD_SCUMM_MSU1_PROGRAMS:-0}" == "1" ]]; then
    MSU_PROGRAM_PACKAGE="$MSU_PROGRAM_STORAGE_DIR/scumm-programs.msu"
    if [[ ! -s "$MSU_PROGRAM_PACKAGE" ]]; then
        echo "Compiler did not produce the SCUMM ProgramUnit SAMEPKG: $MSU_PROGRAM_PACKAGE" >&2
        exit 1
    fi
    "$PYTHON" tools/generate_snes_msu1_directory.py "$MSU_PROGRAM_PACKAGE" \
        --include runtime/snes/generated/msu1_package.inc.pasm \
        --manifest "${SAME_SNES_OUTPUT:-build/same-scumm-v5-msu-programs.sfc}.msu1-directory.json"
    # SCUMM consumes the generated package directory directly. The provider's
    # standalone read-case vectors belong only to the Winston diagnostic
    # personality, but the shared storage module still includes this symbol.
    printf '%s\n' '; No standalone MSU read vectors in the SCUMM consumer build.' \
        > runtime/snes/generated/msu1_read_cases.inc.pasm
    MSU_PROGRAM_ROM="${SAME_SNES_OUTPUT:-build/same-engine-host.sfc}"
    MSU_PROGRAM_STEM="${MSU_PROGRAM_ROM##*/}"
    MSU_PROGRAM_STEM="${MSU_PROGRAM_STEM%.sfc}"
    MSU_PROGRAM_DEST_DIR="$(dirname "$MSU_PROGRAM_ROM")"
    mkdir -p "$MSU_PROGRAM_DEST_DIR"
    MSU_PROGRAM_DEST="$MSU_PROGRAM_DEST_DIR/$MSU_PROGRAM_STEM.msu"
    if [[ -e "$MSU_PROGRAM_DEST" ]]; then
        if ! cmp -s "$MSU_PROGRAM_PACKAGE" "$MSU_PROGRAM_DEST"; then
            echo "Refusing to overwrite non-identical SCUMM MSU package: $MSU_PROGRAM_DEST" >&2
            exit 1
        fi
    else
        cp "$MSU_PROGRAM_PACKAGE" "$MSU_PROGRAM_DEST"
    fi
    if [[ -n "${SAME_MSU1_LIVE_ROOM_PCM_TRACK:-}" ]]; then
        MSU_ROOM_PCM_DEST="$MSU_PROGRAM_DEST_DIR/$MSU_PROGRAM_STEM-$SAME_MSU1_LIVE_ROOM_PCM_TRACK.pcm"
        if [[ -e "$MSU_ROOM_PCM_DEST" ]]; then
            if ! cmp -s "$SAME_MSU1_LIVE_ROOM_PCM_SOURCE" "$MSU_ROOM_PCM_DEST"; then
                echo "Refusing to overwrite non-identical live-room PCM sidecar: $MSU_ROOM_PCM_DEST" >&2
                exit 1
            fi
        else
            cp "$SAME_MSU1_LIVE_ROOM_PCM_SOURCE" "$MSU_ROOM_PCM_DEST"
        fi
    fi
else
    printf '%s\n' '; Generated empty MSU-1 package directory (provider disabled).' \
        > runtime/snes/generated/msu1_package.inc.pasm
    printf '%s\n' '; Generated empty MSU-1 test vectors (diagnostic engine disabled).' \
        > runtime/snes/generated/msu1_read_cases.inc.pasm
    # main.pasm includes the SCUMM ProgramUnit directory unconditionally;
    # Poppy resolves include paths before evaluating the feature guards.
    printf '%s\n' '; Generated empty SCUMM ProgramUnit directory (MSU programs disabled).' \
        > runtime/snes/generated/scumm_v5_msu_programs.inc.pasm
fi
"$PYTHON" tools/generate_snes_engine_selection.py "${ENGINE_SELECTION_ARGS[@]}"
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
elif [[ "$SAME_SNES_CARRIER" == "sa1_bwram" ]]; then
    CARRIER_ARGS+=(--rom-size-code 0x0C)
elif [[ "${SAME_BUILD_SCUMM_M23A:-0}" == "1" ]]; then
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
VIDEO_SURFACE_ARGS=()
if [[ "${SAME_BUILD_SCUMM_ROOM_VISUAL:-0}" == "1" ]]; then
    VIDEO_SURFACE_ARGS+=(--surface-available)
fi
"$PYTHON" tools/generate_snes_video_overlay.py \
    --overlay "$SAME_SNES_VIDEO_OVERLAY" --carrier "$SAME_SNES_CARRIER" \
    --backend "$SAME_SNES_VIDEO_BACKEND" --manifest "$VIDEO_OVERLAY_MANIFEST" \
    "${VIDEO_SURFACE_ARGS[@]}"
if [[ "$SAME_SNES_VIDEO_OVERLAY" == "bg2_index4" ]]; then
    if [[ "${SAME_SNES_ENGINE:-demo}" != "scumm_v5" ]]; then
        echo "bg2_index4 production subtitle overlay currently requires scumm_v5" >&2
        exit 1
    fi
    "$PYTHON" tools/generate_snes_scumm_charset.py \
        --archive "${SAME_FATE_ARCHIVE:?Set SAME_FATE_ARCHIVE to a user-supplied archive}" \
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
# Poppy resolves include paths before evaluating surrounding .if blocks.
# Emit deterministic empty files for feature-gated generated includes when
# their producer is inactive; otherwise a clean checkout can accidentally
# depend on ignored outputs left by a different build profile.
if [[ "${SAME_BUILD_SCUMM_M22:-0}" != "1" ]]; then
    printf '%s\n' '; Generated empty music-sections include (M22 disabled).' \
        > runtime/snes/generated/music_sections.inc.pasm
fi
if [[ "${SAME_BUILD_SCUMM_M20:-0}" != "1" ]]; then
    printf '%s\n' '; Generated empty save-identity include (M20 disabled).' \
        > runtime/snes/generated/save_identity.inc.pasm
fi
if [[ "${SAME_BUILD_SCUMM_ROOM_VISUAL:-0}" != "1" ]]; then
    printf '%s\n' '; Generated empty room-visual include (room visuals disabled).' \
        > runtime/snes/generated/scumm_v5_room_visuals.inc.pasm
fi
if [[ "${SAME_BUILD_SCUMM_ROOM_VISUAL:-0}" != "1" || \
      "${SAME_BUILD_SCUMM_CONTROLLER_FIXTURE:-0}" != "1" ]]; then
    printf '%s\n' '; Generated empty actor-sprite include (fixture sprites disabled).' \
        > runtime/snes/generated/scumm_v5_actor_sprite.inc.pasm
    printf '%s\n' '; Generated empty object-sprite include (fixture sprites disabled).' \
        > runtime/snes/generated/scumm_v5_object_sprite.inc.pasm
fi
if [[ "${SAME_SNES_ENGINE:-demo}" != "scumm_v5" ]]; then
    printf '%s\n' '; Generated empty SCUMM variable include (SCUMM engine disabled).' \
        > runtime/snes/generated/scumm_v5_variables.inc.pasm
fi
if [[ "${SAME_SNES_ENGINE:-demo}" == "scumm_v5" ]]; then
    VARIABLE_PROFILE="${SAME_SNES_PROFILE:-$SAME_FATE_PROFILE}"
    VARIABLE_ARGS=(--profile "$VARIABLE_PROFILE"
        --include runtime/snes/generated/scumm_v5_variables.inc.pasm
        --manifest "${SAME_SNES_OUTPUT%.sfc}.variables.json")
    if [[ "${SAME_BUILD_SCUMM_CONTROLLER_CONFORMANCE:-0}" == "1" ]]; then
        VARIABLE_ARGS=(--synthetic --profile examples/profiles/scumm_v5_controller_conformance.json
            --include runtime/snes/generated/scumm_v5_variables.inc.pasm
            --manifest "${SAME_SNES_OUTPUT%.sfc}.variables.json")
    elif [[ "${SAME_SCUMM_SYNTHETIC_VARIABLES:-0}" == "1" ]]; then
        VARIABLE_ARGS+=(--synthetic)
    elif [[ -n "${SAME_FATE_ARCHIVE:-}" ]]; then
        VARIABLE_ARGS+=(--archive "$SAME_FATE_ARCHIVE")
    else
        echo "SCUMM v5 build requires SAME_FATE_ARCHIVE or explicit SAME_SCUMM_SYNTHETIC_VARIABLES=1" >&2
        exit 1
    fi
    "$PYTHON" tools/generate_snes_scumm_variables.py "${VARIABLE_ARGS[@]}"
fi
"$PYTHON" tools/manifest_poppy_inputs.py \
    --root "$ROOT" --main runtime/snes/main.pasm \
    --output "${SAME_SNES_OUTPUT%.sfc}.poppy-inputs.json"
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
ROM_AUDIT_ARGS=(--carrier "$SAME_SNES_CARRIER" --manifest "$CARRIER_MANIFEST")
if [[ "$SAME_SNES_CARRIER" == "lorom" ]]; then
    ROM_AUDIT_ARGS+=(--map "$SAME_SNES_MAP")
fi
"$PYTHON" tools/audit_snes_rom.py "$SAME_SNES_OUTPUT" "${ROM_AUDIT_ARGS[@]}"
sha256sum "$SAME_SNES_OUTPUT"
"$PYTHON" tools/write_build_identity.py \
    --rom "$SAME_SNES_OUTPUT" \
    --map "$SAME_SNES_MAP" \
    --listing "$SAME_SNES_LISTING" \
    --output "${SAME_SNES_OUTPUT%.sfc}.build_identity.json" \
    --poppy-sha256 "$POPPY_SHA256" \
    --carrier-manifest "$CARRIER_MANIFEST" \
    --video-backend-manifest "$VIDEO_BACKEND_MANIFEST" \
    --video-overlay-manifest "$VIDEO_OVERLAY_MANIFEST"

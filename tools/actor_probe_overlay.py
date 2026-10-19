"""Explicit diagnostic-only overlay for SAME's existing SCUMM package builder.

Call before serializing the NativeProgramDirectory and before building
ProgramUnit storage. All inputs are copied; no source archive is modified.
Provided under the Unlicense/public-domain dedication.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
from typing import Mapping

from actor_probe_program import ProbeConfig, build_probe

SCRIPT_KINDS = {'GLOBAL', 'SCRP', 'ENCD', 'EXCD', 'LSCR',
                'ROOM_ENTRY', 'ROOM_EXIT', 'ROOM_LOCAL'}
OBJECT_KINDS = {'OBJECT', 'OBCD'}


def apply_actor_probe(directory: Mapping, bodies: Mapping[str, bytes],
                      page_metadata: Mapping | None, config: ProbeConfig,
                      *, diagnostic_authorized: bool = False) -> tuple[dict, dict, dict, dict]:
    if not diagnostic_authorized:
        raise ValueError('synthetic script replacement requires explicit diagnostic authorization')
    config.validate()
    document = deepcopy(dict(directory))
    entries = document.get('entries')
    if not isinstance(entries, list) or not entries:
        raise ValueError('expected NativeProgramDirectory.document with entries')
    if document.get('diagnostic_overlay'):
        raise ValueError('input already has a diagnostic overlay; use pristine compiler inputs')
    identities = [str(entry['identity']) for entry in entries]
    ids = [int(entry['program_unit_id']) for entry in entries]
    if len(set(identities)) != len(identities) or sorted(ids) != list(range(len(ids))):
        raise ValueError('nonunique identities or nondense IDs')
    if set(identities) != set(bodies):
        raise ValueError('directory/body identity mismatch')
    boot = [entry for entry in entries
            if str(entry['kind']).upper() in {'GLOBAL', 'SCRP'}
            and entry.get('number') == config.boot_script]
    if len(boot) != 1:
        raise ValueError('boot script must resolve to exactly one global')
    program, program_report = build_probe(config)
    boot_identity = str(boot[0]['identity'])
    if len(program) > len(bodies[boot_identity]):
        raise ValueError('original boot carrier too short for length-preserving probe')
    out_bodies = {key: bytes(value) for key, value in bodies.items()}
    metadata = deepcopy(dict(page_metadata or {}))
    ledger = []
    for entry in entries:
        identity = str(entry['identity'])
        original = out_bodies[identity]
        original_sha = hashlib.sha256(original).hexdigest()
        if not original or len(original) != int(entry['length']) or original_sha != entry['sha256']:
            raise ValueError(f'input body does not match directory: {identity}')
        kind = str(entry['kind']).upper()
        if kind not in SCRIPT_KINDS | OBJECT_KINDS:
            raise ValueError(f'unrecognized carrier kind: {kind}')
        if kind in OBJECT_KINDS:
            continue
        if identity == boot_identity:
            replacement = program + b'\xa0' * (len(original) - len(program))
            spans = program_report['instruction_spans'] + [[i, 1] for i in range(len(program), len(original))]
        else:
            replacement = b'\xa0' * len(original)
            spans = [[i, 1] for i in range(len(original))]
        new_sha = hashlib.sha256(replacement).hexdigest()
        out_bodies[identity] = replacement
        metadata[identity] = {'instruction_spans': spans, 'opaque_ranges': []}
        entry['sha256'] = new_sha
        entry['source_provenance'] = {
            'kind': 'synthetic-actor-proof-overlay',
            'original_source_provenance': entry.get('source_provenance'),
            'original_body_sha256': original_sha,
            'diagnostic_body_sha256': new_sha,
            'body_pc_coordinate': 'program-body-relative',
            'not_authentic_game_script': True,
        }
        ledger.append({'identity': identity, 'program_unit_id': entry['program_unit_id'],
                       'length': len(original), 'original_sha256': original_sha,
                       'diagnostic_sha256': new_sha})
    report = {'schema': 'same-actor-proof-overlay-v1', 'kind': 'SYNTHETIC_GRAPHICS_DIAGNOSTIC',
              'production_release_eligible': False, 'gameplay_authentic': False,
              'boot_identity': boot_identity,
              'boot_program_unit_id': boot[0]['program_unit_id'],
              'source_ids_preserved': True, 'all_body_lengths_preserved': True,
              'native_runtime_code_added': 0, 'program': program_report,
              'replacements': ledger, 'untouched_object_carriers': len(entries) - len(ledger)}
    document['diagnostic_overlay'] = {
        'kind': report['kind'], 'production_release_eligible': False,
        'boot_identity': report['boot_identity'], 'driver_sha256': program_report['sha256'],
    }
    return document, out_bodies, metadata, report

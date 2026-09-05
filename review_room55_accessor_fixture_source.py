def room55_accessor_scripts():
    """Copyright-free target exercise for the generated accessor."""
    program = bytearray()
    for index in range(64):
        x = 3 + max(0, index - 1) * 8
        program.extend((0x01, 1, x & 0xFF, x >> 8, 0, 0, 0x80))
    program.append(0x00)
    return start_script(200) + bytes((0x00,)), ((200, bytes(program)),)


def room55_movement_fixture():
    """The companion target fixture uses production movement, not a mock."""
    target_x = 499
    program = bytes((0x1E, 1, target_x & 0xff, target_x >> 8,
                     0, 0, 0xAE, 0x00))
    return start_script(200) + bytes((0x00,)), ((200, program),)


# The generated accessor's complete record body is nine little-endian words
# (eight coordinates followed by scale).  Its caller contract is explicit:
# X is the unsigned box index on entry, X is clobbered by the byte-offset
# calculation, A is restored to 8-bit before RTL, and the caller restores its
# actor/output index after the fetch.  The work record is temporary and cannot
# be retained across a nested geometry query.

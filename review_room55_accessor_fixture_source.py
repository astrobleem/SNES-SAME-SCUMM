def room55_accessor_scripts():
    """Copyright-free target exercise for the generated accessor."""
    program = bytearray()
    for index in range(64):
        x = 3 + max(0, index - 1) * 8
        program.extend((0x01, 1, x & 0xFF, x >> 8, 0, 0, 0x80))
    program.append(0x00)
    return start_script(200) + bytes((0x00,)), ((200, bytes(program)),)

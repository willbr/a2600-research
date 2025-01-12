from pathlib import Path

import struct
import sys

filename = Path(sys.argv[1])

print(filename)

with open(filename, 'rb') as f:
    data = f.read()

i = 0
while i < len(data):
    n = data[i]
    if n != 0: break
    i += 1

while i < len(data):
    opcode = struct.unpack_from('<B', data, i)[0]
    opcode_size = 1
    if opcode == 0x00:
        asm = 'brk'
    elif opcode == 0x4c:
        n = struct.unpack_from('<H', data, i+1)[0]
        opcode_size = 3
        asm = f'jmp ${n:04x}'
    elif opcode == 0x78:
        asm = 'sei'
    elif opcode == 0x8d:
        n = struct.unpack_from('<H', data, i+1)[0]
        opcode_size = 3
        asm = f'sta ${n:04x}'
    elif opcode == 0x95:
        n = struct.unpack_from('<B', data, i+1)[0]
        opcode_size = 2
        asm = f'sta ${n:02x},x'
    elif opcode == 0x9a:
        asm = 'txs'
    elif opcode == 0xa2:
        n = struct.unpack_from('<B', data, i+1)[0]
        opcode_size = 2
        asm = f'ldx #${n:02x}'
    elif opcode == 0xa9:
        n = struct.unpack_from('<B', data, i+1)[0]
        opcode_size = 2
        asm = f'lda #${n:02x}'
    elif opcode == 0xca:
        asm = 'dex'
    elif opcode == 0xd0:
        n = struct.unpack_from('<B', data, i+1)[0]
        opcode_size = 2
        asm = f'bne ${n:02x}'
    elif opcode == 0xd8:
        asm = 'cld'
    elif opcode == 0xea:
        asm = 'nop'
    else:
        asm = 'unknown opcode'
    
    chunk = struct.unpack_from(f'<{opcode_size}B', data, i)
    hex_values = (' '.join(f'{b:02x}' for b in chunk)).ljust(8, ' ')

    print(f'{i:04x} {hex_values} {asm}')
    i += opcode_size

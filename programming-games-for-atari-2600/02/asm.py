from rich.traceback import install
install(show_locals=True)

from pathlib import Path

import sys
import re
import struct

def split_comments(lst):
    try:
        index = lst.index('comment')
        return lst[:index], ' '.join(lst[index+1:])
    except ValueError:
        return lst, ''

def hex_dump(data: bytes, bytes_per_line: int = 16, skip_zeros: bool = True) -> None:
    """
    Create a hex dump of a byte array, showing hex values and ASCII representation.
    Skips lines containing only zero bytes by default.
    
    Args:
        data: Bytes to dump
        bytes_per_line: Number of bytes to show per line (default 16)
        skip_zeros: If True, skip lines containing only zeros (default True)
    """
    prev_zeros = False  # Track if previous line was zeros
    
    for i in range(0, len(data), bytes_per_line):
        # Get the bytes for this line
        chunk = data[i:i + bytes_per_line]
        
        # Check if line is all zeros
        if skip_zeros and all(b == 0 for b in chunk):
            if not prev_zeros:
                print("*")  # Print marker for first zero line
                prev_zeros = True
            continue
        prev_zeros = False
        
        # Create hex representation
        hex_values = ' '.join(f'{b:02x}' for b in chunk)
        
        # Pad hex values to align ASCII representation
        hex_padding = ' ' * (3 * (bytes_per_line - len(chunk)))
        
        # Create ASCII representation
        ascii_values = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in chunk)
        
        # Print the line with offset, hex values, and ASCII representation
        print(f'{i:08x}  {hex_values}{hex_padding}  |{ascii_values}|')

def parse_arg(arg):
    c = arg[0]
    if c == '$':
        n = int(arg[1:], 16)
    else:
        try:
            n = int(arg, 10)
        except ValueError:
            n = None

    if n is None:
        return arg
    else:
        return n

def tokenise_lines(data):
    lines = data.split('\n')
    i = 0
    while True:
        line_tokens = [i]

        try:
            line = lines[i]
        except IndexError:
            break

        line = line.lstrip(' ')
        #print(f'{i} {line}')

        j = 0
        tail = line
        while True:
            elems = re.split(r'([ ]+|[,;])', tail, maxsplit=1)
            #print(f'{elems=}')
            match elems:
                case token, sep, tail:
                    if token == '':
                        pass
                    elif token[0] == ';':
                        line_tokens.extend(('comment', ''.join((token[1:], sep, tail)).strip()))
                        break
                    else:
                        line_tokens.append(token)

                    if sep == ';':
                        line_tokens.extend(('comment', tail))
                        break
                case [token]:
                    if token == '':
                        break
                    elif token[0] == ';':
                        line_tokens.extend(('comment', token[1:]))
                        break
                    line_tokens.append(token)
                    break
                case _:
                    assert False
                    break


        #print(f'{line_tokens=}')
        yield line_tokens

        i += 1



def emit(byte_array, offset=None):
    global pc

    size = len(byte_array)

    if offset is None:
        offset = pc
        pc += size

    program[offset:offset+size] = byte_array

def set_origin(*args, comment):
    global pc
    arg = parse_arg(args[0])
    assert isinstance(arg, int)
    pc = arg
    #print(f'set origin 0x{arg:04x}')

def create_label(name):
    #print(f'create label {name=} at ${pc:04x}')
    assert name not in labels
    labels[name] = pc

def emit_sei(*args, comment):
    assert args == ()
    #print('sei')
    emit(b'\x78')

def emit_cld(*args, comment):
    assert args == ()
    #print('cld')
    emit(b'\xd8')

def emit_ldx(*args, comment):
    match args:
        case [lhs, rhs]:
            lhs = parse_arg(lhs)
            rhs = parse_arg(rhs)
            assert False
        case [arg]:
            arg = parse_arg(arg)
            if isinstance(arg, str):
                if arg[0] == '#': # immediate value
                    arg = parse_arg(arg[1:])
                    assert isinstance(arg, int)
                    emit(struct.pack('<BB', 0xa2, arg))
                else:
                    assert False
    #print(f'ldx {args=}')

def emit_lda(*args, comment):
    match args:
        case [lhs, rhs]:
            lhs = parse_arg(lhs)
            rhs = parse_arg(rhs)
            assert False
        case [arg]:
            arg = parse_arg(arg)
            if isinstance(arg, str):
                if arg[0] == '#': # immediate value
                    arg = parse_arg(arg[1:])
                    assert isinstance(arg, int)
                    emit(struct.pack('<BB', 0xa9, arg))
                else:
                    assert False

def emit_txs(*args, comment):
    assert args == ()
    #print('txs')
    emit(b'\x9a')

def emit_sta(*args, comment):
    match args:
        case [lhs, rhs]:
            lhs = parse_arg(lhs)
            rhs = parse_arg(rhs)
            if rhs == 'x':
                assert isinstance(lhs, int)
                if lhs > 255:
                    assert False
                else:
                    emit(struct.pack('<BB', 0x95, lhs))
        case [arg]:
            arg = parse_arg(arg)
            if isinstance(arg, str):
                if arg[0] == '#': # immediate value
                    assert False
                    arg = parse_arg(arg[1:])
                    assert isinstance(arg, int)
                    emit(struct.pack('<BB', 0xa9, arg))
                else:
                    emit(struct.pack('<BH', 0x8d, 0xcafe))
                    references.append((arg, 'u16', pc+1))
    #print(f'sta {args=}')

def emit_dex(*args, comment):
    assert args == ()
    #print('dex')
    emit(b'\xca')

def emit_bne(*args, comment): # 0xd0
    assert len(args) == 1
    arg = parse_arg(args[0])
    if isinstance(arg, str):
        references.append((arg, 'r8', pc+1))
        rel_offset = 0xff
    else:
        rel_offset = arg
        assert False
    emit(struct.pack('<BB', 0xd0, rel_offset))
    #print(f'bne {args=}')

def emit_nop(*args, comment):
    assert args == ()
    #print(f'nop {args=}, {comment=}')
    emit(b'\xea')

def emit_jmp(*args, comment):
    assert len(args) == 1
    arg = parse_arg(args[0])
    if isinstance(arg, str):
        references.append((arg, 'u16', pc+1))
        dst = 0xcafe
    else:
        assert False
    emit(struct.pack('<BH', 0x4c, dst))

def emit_word(*args, comment):
    #print(f'.word {args=}')
    assert len(args) == 1
    arg = parse_arg(args[0])
    if isinstance(arg, str):
        references.append((arg, 'u16', pc))
        n = 0xcafe
    else:
        n = arg

    packed = struct.pack('<H', n)
    emit(packed)

def do_nothing(*args, comment):
    pass

commands = {
        'org': set_origin,
        'comment': do_nothing,
        'processor': do_nothing,
        'include': do_nothing,
        'sei': emit_sei,
        'cld': emit_cld,
        'lda': emit_lda,
        'ldx': emit_ldx,
        'txs': emit_txs,
        'sta': emit_sta,
        'dex': emit_dex,
        'bne': emit_bne,
        'nop': emit_nop,
        'jmp': emit_jmp,
        '.word': emit_word,
}

program = bytearray(4096)
references = []
labels = {
        'colubk': 0x8008,
        'colupf': 0x8008,
        'wsync':  0x8008,
        'vsync':  0x8008,
        'resbl':  0x8008,
        'vblank': 0x8008,
        'enabl':  0x8008,
        }
pc = 0

def main(filename):

    global pc

    with open(filename, 'r', encoding='utf8') as f:
        data = f.read()

    lines = list(tokenise_lines(data))

    for line in lines:
        #print(line)
        match line:
            case line_num, cmd_name, *args:
                args, comment = split_comments(args)
                #print(f'{line_num=} {cmd_name=} {args=} {comment=}')
                if cmd_name[-1] == ':':
                    assert args == []
                    create_label(name=cmd_name[:-1])
                else:
                    fn = commands.get(cmd_name, None)
                    assert fn is not None, f'missing {cmd_name=}'
                    fn(*args, comment=comment)
            case [line_num]:
                pass


    for label_name, var_size, offset in references:
        n = labels[label_name]
        if var_size == 'u16':
            packed = struct.pack('<H', n)
            emit(packed, offset)
        elif var_size == 'r8':
            rel_offset = n - offset
            packed = struct.pack('<b', rel_offset)
            emit(packed, offset)
        else:
            assert False

    hex_dump(program)
    #print(dir(filename))
    with open(filename.with_suffix('.bin'), 'wb') as f:
        f.write(program)


if __name__ == '__main__':
    main(filename=Path(sys.argv[1]))


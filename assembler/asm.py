from rich.traceback import install
install(show_locals=True)

# TODO add ORD and Data Directives
# TODO write listings file
# TODO improve error messages

class Assembler:
    def __init__(self):
        # Extended instruction set with more addressing modes (not exhaustive)
        # Only some mnemonics are shown; add more as needed.
        self.instructions = {
            'LDA': {
                'immediate': 0xA9,
                'zeropage': 0xA5,
                'zeropage_x': 0xB5,
                'absolute': 0xAD,
                'absolute_x': 0xBD,
                'absolute_y': 0xB9,
                'indirect_x': 0xA1,
                'indirect_y': 0xB1
            },
            'STA': {
                'zeropage': 0x85,
                'zeropage_x': 0x95,
                'absolute': 0x8D,
                'absolute_x': 0x9D,
                'absolute_y': 0x99,
                'indirect_x': 0x81,
                'indirect_y': 0x91
            },
            'ADC': {
                'immediate': 0x69,
                'zeropage': 0x65,
                'zeropage_x': 0x75,
                'absolute': 0x6D,
                'absolute_x': 0x7D,
                'absolute_y': 0x79,
                'indirect_x': 0x61,
                'indirect_y': 0x71
            },
            'SBC': {
                'immediate': 0xE9,
                'zeropage': 0xE5,
                'zeropage_x': 0xF5,
                'absolute': 0xED,
                'absolute_x': 0xFD,
                'absolute_y': 0xF9,
                'indirect_x': 0xE1,
                'indirect_y': 0xF1
            },
            'CMP': {
                'immediate': 0xC9,
                'zeropage': 0xC5,
                'zeropage_x': 0xD5,
                'absolute': 0xCD,
                'absolute_x': 0xDD,
                'absolute_y': 0xD9,
                'indirect_x': 0xC1,
                'indirect_y': 0xD1
            },
            'JMP': {
                'absolute': 0x4C,
                'indirect': 0x6C  # JMP ($xxxx)
            },
            'BEQ': {'relative': 0xF0},
            'BNE': {'relative': 0xD0},
            'INX': {'implied': 0xE8},
            'DEX': {'implied': 0xCA}
        }
        self.symbols = {}
        self.output = []
        self.line_info = []

    def parse_value(self, value_str):
        """
        Convert a string value to integer, handling:
          - Hex notation like $A9 or $FF00
          - Decimal (if no $)
        """
        value_str = value_str.strip()
        if value_str.startswith("$"):
            return int(value_str[1:], 16)
        return int(value_str)

    def parse_operand(self, operand):
        """
        Parse an operand into (addressing_mode, value).
        We handle the following forms:
          #$xx        => immediate
          $xx         => zero page or absolute
          $xx,X       => zero page,X or absolute,X
          $xx,Y       => zero page,Y or absolute,Y
          ($xx,X)     => (indirect,X)
          ($xx),Y     => (indirect),Y
          ($xxxx)     => indirect
          label       => symbol (later resolved to zero page / absolute)
          etc.
        """
        operand = operand.strip()

        # Immediate addressing (e.g. "#$10")
        if operand.startswith("#"):
            return "immediate", self.parse_value(operand[1:])

        # Check for parentheses => indirect or (indirect_x)/(indirect_y)
        if operand.startswith("(") and operand.endswith(")"):
            # e.g. "($10,X)" or "($10),Y" or "($1000)"
            inner = operand[1:-1].strip()

            # If there's a comma inside the parentheses
            if "," in inner:
                # e.g. ($10,X)
                parts = inner.split(",")
                base_str = parts[0].strip()   # e.g. "$10"
                reg_str = parts[1].strip().upper()  # "X" or "Y" presumably
                if reg_str == "X":
                    # Indirect,X
                    return "indirect_x", self.parse_value(base_str)
                else:
                    raise ValueError(f"Unsupported register {reg_str} in indirect addressing")
            else:
                # e.g. "($10),Y" => note that the operand ends with ")"
                # Actually means something like "($10),Y" => indirect_y
                if operand.endswith("),Y"):
                    # strip the trailing ",Y"
                    # operand = ($10),Y
                    # so inside parentheses is "$10"
                    # Then parse the base.
                    base_inner = operand[:-3]  # remove ",Y"
                    base_inner = base_inner[1:-1].strip()  # remove outer parentheses
                    return "indirect_y", self.parse_value(base_inner)
                else:
                    # Plain indirect e.g. "($1000)" for JMP
                    return "indirect", self.parse_value(inner)

        # If there's a comma but no parentheses => absolute_x, absolute_y, ...
        if "," in operand:
            # e.g. "$1234,X" or "$80,Y"
            parts = operand.split(",")
            base_str = parts[0].strip()  # e.g. "$1234"
            reg_str = parts[1].strip().upper()  # e.g. "X" or "Y"
            base_val = self.parse_value(base_str)

            # Distinguish zero page vs absolute
            if base_val < 0x100:
                if reg_str == "X":
                    return "zeropage_x", base_val
                elif reg_str == "Y":
                    return "zeropage_y", base_val
                else:
                    raise ValueError(f"Invalid register {reg_str}")
            else:
                if reg_str == "X":
                    return "absolute_x", base_val
                elif reg_str == "Y":
                    return "absolute_y", base_val
                else:
                    raise ValueError(f"Invalid register {reg_str}")

        # Plain "$xxxx" or "$xx" => might be zero page or absolute
        if operand.startswith("$"):
            base_val = self.parse_value(operand)
            if base_val < 0x100:
                return "zeropage", base_val
            else:
                return "absolute", base_val

        # If it doesn’t match any special prefix => assume symbol
        return "symbol", operand

    def get_instruction_length(self, opcode, addr_mode):
        # If we see 'symbol' in the first pass, guess a length:
        if addr_mode == "symbol":
            # Branch => 2 bytes
            if opcode in ["BEQ", "BNE", "BCC", "BCS", "BMI", "BPL", "BVC", "BVS"]:
                return 2
            # JMP or JSR => definitely 3
            if opcode in ["JMP", "JSR"]:
                return 3
            # Else guess 3 for safety (typical for absolute).
            return 3
        
        # Normal known modes:
        if addr_mode == "implied":
            return 1
        elif addr_mode in ["immediate", "zeropage", "relative",
                           "zeropage_x", "zeropage_y", "indirect_x", "indirect_y"]:
            return 2
        elif addr_mode in ["absolute", "absolute_x", "absolute_y", "indirect"]:
            return 3

        raise ValueError(f"Unknown addressing mode: {addr_mode}")

    def parse_line(self, line):
        # 1) Remove anything after the first semicolon
        line = line.split(";", 1)[0].strip()
        
        # 2) Skip empty lines
        if not line:
            return None

        # 3) Check for label
        if ":" in line:
            label, rest = line.split(":", 1)
            label = label.strip()
            rest = rest.strip()
            return {"type": "label", "label": label, "rest": rest}

        # 4) Extract opcode and operand
        parts = line.split(maxsplit=1)
        opcode = parts[0].upper()

        if opcode not in self.instructions:
            raise ValueError(f"Unknown instruction: {opcode}")

        if len(parts) == 1:
            # e.g. INX (implied mode)
            return {
                "type": "instruction",
                "opcode": opcode,
                "mode": "implied",
                "value": None
            }
        else:
            # e.g. LDA #$05
            mode, value = self.parse_operand(parts[1])
            return {
                "type": "instruction",
                "opcode": opcode,
                "mode": mode,
                "value": value
            }

    def first_pass(self, lines):
        """
        First pass: 
          - Collect symbols (labels) and their corresponding addresses. 
          - Record each instruction's address in line_info.
        """
        current_address = 0
        self.line_info = []

        for line in lines:
            parsed = self.parse_line(line)
            if not parsed:
                self.line_info.append({"parsed": None, "address": None})
                continue

            if parsed["type"] == "label":
                # Mark label => current address
                self.symbols[parsed["label"]] = current_address

                # Possibly parse an instruction on the same line
                if parsed["rest"]:
                    instr = self.parse_line(parsed["rest"])
                    if instr and instr["type"] == "instruction":
                        self.line_info.append({"parsed": instr, "address": current_address})
                        current_address += self.get_instruction_length(
                            instr["opcode"], instr["mode"]
                        )
                    else:
                        self.line_info.append({"parsed": None, "address": None})
                else:
                    self.line_info.append({"parsed": None, "address": None})

            elif parsed["type"] == "instruction":
                self.line_info.append({"parsed": parsed, "address": current_address})
                current_address += self.get_instruction_length(
                    parsed["opcode"], parsed["mode"]
                )

    def assemble(self, source):
        """Assemble source code into machine code (bytes)."""
        lines = source.splitlines()
        
        # ----- First Pass -----
        self.first_pass(lines)

        # ----- Second Pass -----
        self.output = []
        for i, line_data in enumerate(self.line_info):
            parsed = line_data["parsed"]
            line_address = line_data["address"]

            if not parsed or parsed["type"] != "instruction":
                continue

            opcode = parsed["opcode"]
            mode = parsed["mode"]
            value = parsed["value"]

            # Symbol resolution
            if mode == "symbol":
                if value not in self.symbols:
                    raise ValueError(f"Undefined symbol: {value}")
                symbol_address = self.symbols[value]

                # Some instructions must remain 'absolute' or 'zeropage' 
                # or become 'relative' if it's a branch. But let's keep it simple:
                # If it's a branch instruction, mode is already 'relative'.
                # Otherwise, check if symbol fits in zero page or not:
                if opcode == "JMP":
                    # JMP absolute or indirect
                    # We'll assume absolute if the user wrote "JMP symbol"
                    mode = "absolute"  
                    value = symbol_address
                else:
                    if symbol_address < 0x100:
                        mode = "zeropage"
                        value = symbol_address
                    else:
                        mode = "absolute"
                        value = symbol_address

            # If the instruction’s mode is 'relative' => branch offset
            if mode == "relative":
                # value is presumably a label. Ensure it's defined:
                if value not in self.symbols:
                    raise ValueError(f"Undefined symbol for branch: {value}")
                branch_target = self.symbols[value]
                offset = branch_target - (line_address + 2)  # next PC after opcode+offset
                if not (-128 <= offset <= 127):
                    raise ValueError(
                        f"Branch out of range at ${line_address:04X} to '{value}' (${branch_target:04X})"
                    )
                offset &= 0xFF
                value = offset

            # Validate addressing mode in the instruction dictionary
            if mode not in self.instructions[opcode]:
                raise ValueError(f"Invalid addressing mode '{mode}' for opcode {opcode}")

            # Emit the opcode
            self.output.append(self.instructions[opcode][mode])

            # Emit operand bytes based on mode
            if mode in [
                "immediate", "zeropage", "zeropage_x", "zeropage_y",
                "relative", "indirect_x", "indirect_y"
            ]:
                self.output.append(value & 0xFF)
            elif mode in ["absolute", "absolute_x", "absolute_y", "indirect"]:
                self.output.append(value & 0xFF)
                self.output.append((value >> 8) & 0xFF)
            # "implied" => no extra bytes

        return bytes(self.output)


def main():
    import sys
    import os
    
    if len(sys.argv) != 2:
        print("Usage: python assembler.py <input_file>")
        sys.exit(1)
        
    input_file = sys.argv[1]
    output_file = os.path.splitext(input_file)[0] + '.bin'
    
    try:
        with open(input_file, 'r') as f:
            source_code = f.read()
    except FileNotFoundError:
        print(f"Error: File '{input_file}' not found")
        sys.exit(1)
    except IOError as e:
        print(f"Error reading file: {e}")
        sys.exit(1)
        
    assembler = Assembler()
    binary = assembler.assemble(source_code)
    
    # Print assembly listing
    print("Assembly listing:")
    for i, byte in enumerate(binary):
        print(f"{i:04X}: {byte:02X}")
        
    # Write binary output
    with open(output_file, 'wb') as f:
        f.write(binary)
    print(f"\nBinary written to {output_file}")
        

if __name__ == "__main__":
    main()

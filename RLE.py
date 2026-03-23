import os
def RLE_encode(data, Ms=1, Mc=1):
    result = bytearray()
    i = 0
    n = len(data)

    if len(data) % Ms != 0:
        raise ValueError(f"Длина данных не кратна Ms")

    if Mc == 1:
        max_len = 127
    else:
        max_len = (1 << (Mc * 8 - 1)) - 1

    while i < n:
        current = data[i:i + Ms]

        if i + Ms < n and current == data[i + Ms:i + 2 * Ms]:
            run_n = 1
            while (i + (run_n + 1) * Ms <= n and
                   data[i:i + (run_n + 1) * Ms] == current * (run_n + 1) and
                   run_n < max_len):
                run_n += 1

            if Mc == 1:
                result.append(run_n)
            else:
                result.extend(run_n.to_bytes(Mc, 'big'))

            result.extend(current)
            i += run_n * Ms

        else:
            dif_n = 1
            while (i + (dif_n + 1) * Ms <= n and dif_n < max_len):
                next = data[i + dif_n * Ms:i + (dif_n + 1) * Ms]
                next_next = data[i + (dif_n + 1) * Ms:i + (dif_n + 2) * Ms] if i + (dif_n + 2) * Ms <= n else None
                if next_next is not None and next == next_next:
                    break
                dif_n += 1
            if Mc == 1:
                result.append(128 + dif_n)
            else:
                control_bytes = dif_n.to_bytes(Mc, 'big')
                result.append(control_bytes[0] | 0x80)
                result.extend(control_bytes[1:])
            result.extend(data[i:i + dif_n * Ms])
            i += dif_n * Ms

    return bytes(result)

def RLE_decode(encoded_data, Ms=1, Mc=1):
    result = bytearray()
    i = 0
    n = len(encoded_data)

    while i < n:
        if Mc == 1:
            control = encoded_data[i]
            i += 1
            is_non_repeat = (control & 0x80) != 0
            length = control & 0x7F if is_non_repeat else control
        else:
            control_bytes = encoded_data[i:i + Mc]
            i += Mc
            is_non_repeat = (control_bytes[0] & 0x80) != 0
            if is_non_repeat:
                restored = bytes([control_bytes[0] & 0x7F]) + control_bytes[1:]
                length = int.from_bytes(restored, 'big')
            else:
                length = int.from_bytes(control_bytes, 'big')
        if is_non_repeat:
            result.extend(encoded_data[i:i + length * Ms])
            i += length * Ms
        else:
            symbol = encoded_data[i:i + Ms]
            i += Ms
            result.extend(symbol * length)

    return bytes(result)

def RLE_encode_string(s):
    return RLE_encode(s.encode('latin-1'))

def RLE_decode_string(encoded_data):
    return RLE_decode(encoded_data).decode('latin-1')

def split_utf8(data):
    symbols = []
    i = 0
    n = len(data)
    while i < n:
        first_byte = data[i]
        if first_byte < 0x80:
            char_len = 1
        elif first_byte < 0xE0:
            char_len = 2
        elif first_byte < 0xF0:
            char_len = 3
        else:
            char_len = 4
        if i + char_len > n:
            return None
        symbols.append(data[i:i + char_len])
        i += char_len
    return symbols

def RLE_encode_utf8(text, Mc=1):
    data = text.encode('utf-8')
    symbols = split_utf8(data)

    if symbols is None:
        return RLE_encode(data, 1, Mc), 1

    max_symbol_len = max(len(s) for s in symbols)

    if max_symbol_len == 1:
        return RLE_encode(data, 1, Mc), 1

    a_data = bytearray()
    for sym in symbols:
        a_data.extend(sym)
        a_data.extend(b'\x00' * (max_symbol_len - len(sym)))
    encoded = RLE_encode(bytes(a_data), max_symbol_len, Mc)
    return encoded, max_symbol_len

def RLE_decode_utf8(encoded_data, Ms, Mc=1):

    a_decoded = RLE_decode(encoded_data, Ms, Mc)

    if Ms == 1:
        return a_decoded.decode('utf-8')

    symbols = []
    i = 0
    n = len(a_decoded)
    while i < n:
        sym_end = i + Ms
        while sym_end > i and a_decoded[sym_end - 1] == 0:
            sym_end -= 1
        if sym_end > i:
            symbols.append(a_decoded[i:sym_end])
        i += Ms
    result = b''.join(symbols)
    return result.decode('utf-8')


print("\nТолько повторяющиеся символы:")
data1 = bytes([0xCF, 0xCF, 0xCF, 0xCF, 0xCF])
encoded1 = RLE_encode(data1)
decoded1 = RLE_decode(encoded1)
print(f"Исходные: {' '.join(f'0x{b:02X}' for b in data1)}")
print(f"Закодированные: {' '.join(f'0x{b:02X}' for b in encoded1)}")
print(f"Декодированные: {' '.join(f'0x{b:02X}' for b in decoded1)}")

print("\nТолько неповторяющиеся символы:")
data2 = bytes([0xCF, 0xCE, 0xCF, 0xCE, 0xCF])
encoded2 = RLE_encode(data2)
decoded2 = RLE_decode(encoded2)
print(f"Исходные: {' '.join(f'0x{b:02X}' for b in data2)}")
print(f"Закодированные: {' '.join(f'0x{b:02X}' for b in encoded2)}")
print(f"Декодированные: {' '.join(f'0x{b:02X}' for b in decoded2)}")

print("\nСмешанные последовательности:")
data3 = bytes([0xCF, 0xCE, 0xCF, 0xCE, 0xCF, 0xCF, 0xCF, 0xCF, 0xCF, 0xCF])
encoded3 = RLE_encode(data3)
decoded3 = RLE_decode(encoded3)
print(f"Исходные: {' '.join(f'0x{b:02X}' for b in data3)}")
print(f"Закодированные: {' '.join(f'0x{b:02X}' for b in encoded3)}")
print(f"Декодированные: {' '.join(f'0x{b:02X}' for b in decoded3)}")

print("\nСтрока:")
data4 = "АААБББВВВГДЕКПП"
encoded4, Ms = RLE_encode_utf8(data4)
decoded4 = RLE_decode_utf8(encoded4, Ms)
print(f"Исходные: '{data4}' (длина: {len(data4)})")
print(f"Закодированные: {' '.join(f'0x{b:02X}' for b in encoded4)}")
print(f"Декодированные: '{decoded4}'")
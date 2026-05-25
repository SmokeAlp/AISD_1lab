import os
def RLE_encode(data, Ms=1, Mc=1, utf8=False):
    if utf8 and isinstance(data, str):
        encoded, Ms = RLE_encode_utf8(data, Mc)
        return encoded, Ms
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

def RLE_decode(encoded_data, Ms=1, Mc=1, utf8=False):
    if utf8:
        return RLE_decode_utf8(encoded_data, Ms, Mc)
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

class RLEFile:

    MAGIC = b'RLE\x00'

    @staticmethod
    def int_to_bytes(value, size):
        result = bytearray()
        for i in range(size):
            result.append((value >> (i * 8)) & 0xFF)
        return bytes(result)

    @staticmethod
    def bytes_to_int(data):
        result = 0
        for i, byte in enumerate(data):
            result |= (byte << (i * 8))
        return result

    @staticmethod
    def save_compressed(data, file, Ms=1, Mc=1, utf8=False):
        is_text = isinstance(data, str)

        if utf8 and is_text:
            encoded, a_Ms = RLE_encode_utf8(data, Mc)
            Ms = a_Ms
            original_data = data.encode('utf-8')
            original_size = len(original_data)
        elif is_text:
            original_data = data.encode('utf-8')
            encoded = RLE_encode(original_data, Ms, Mc)
            original_size = len(original_data)
        else:
            original_data = data
            encoded = RLE_encode(original_data, Ms, Mc)
            original_size = len(original_data)
            is_text = False

        with open(file, 'wb') as f:
            f.write(RLEFile.MAGIC)
            f.write(bytes([Ms]))
            f.write(bytes([Mc]))
            f.write(bytes([1 if is_text else 0]))
            f.write(RLEFile.int_to_bytes(original_size, 8))
            f.write(RLEFile.int_to_bytes(len(encoded), 8))
            f.write(encoded)
        print(f"Закодированные данные сохранены в: {file}")
        return len(encoded)

    @staticmethod
    def load_compressed(input_file, output_file, decode_str=True):
        with open(input_file, 'rb') as f:
            magic = f.read(4)
            if magic != RLEFile.MAGIC:
                raise ValueError(f"Неверный формат файла: {magic}")

            Ms_b = f.read(1)
            if not Ms_b:
                raise ValueError("Ms")
            Ms = Ms_b[0]
            Mc_b = f.read(1)
            if not Mc_b:
                raise ValueError("Mc")
            Mc = Mc_b[0]
            is_textb = f.read(1)
            if not is_textb:
                raise ValueError("is_text")
            is_text = is_textb[0] == 1
            original_sizeb = f.read(8)
            if len(original_sizeb) != 8:
                raise ValueError("original_size")
            original_size = RLEFile.bytes_to_int(original_sizeb)
            encoded_sizeb = f.read(8)
            if len(encoded_sizeb) != 8:
                raise ValueError("encoded_size")
            encoded_size = RLEFile.bytes_to_int(encoded_sizeb)
            encoded_data = f.read(encoded_size)
            if len(encoded_data) != encoded_size:
                raise ValueError("Неполные данные")

        decoded = RLE_decode(encoded_data, Ms, Mc, is_text)
        if isinstance(decoded, str):
            decoded = decoded.encode('utf-8')

        if len(decoded) > original_size:
                decoded = decoded[:original_size]

        with open(output_file, 'wb') as out_f:
            if decode_str and is_text:
                out_f.write(decoded.encode('utf-8'))
            else:
                out_f.write(decoded)
        print(f"Декодированные данные сохранены в: {output_file}")

    @staticmethod
    def compress_file(input_file, output_file, Ms=1, Mc=1, utf8=False, is_text=False):
        if is_text:
            with open(input_file, 'r', encoding='utf-8') as f:
                data = f.read()
        else:
            with open(input_file, 'rb') as f:
                data = f.read()

        encoded_size = RLEFile.save_compressed(data, output_file, Ms, Mc, utf8)

        original_size = os.path.getsize(input_file)
        kf = original_size / encoded_size

        print(f"Файл: {input_file}")
        print(f"Исходный размер: {original_size:,} байт")
        print(f"Сжатый размер: {encoded_size:,} байт")
        print(f"Коэффициент сжатия: {kf:.2f}")

        return kf

def test():
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
    encoded4, Ms = RLE_encode(data4, utf8=True)
    decoded4 = RLE_decode(encoded4, Ms=Ms, utf8=True)
    print(f"Исходные: '{data4}' (длина: {len(data4)})")
    print(f"Закодированные: {' '.join(f'0x{b:02X}' for b in encoded4)}")
    print(f"Декодированные: '{decoded4}'\n")
    print("\n")

def test_file():
    print("---Тестирование файлов\n")
    RLEFile.compress_file("Результаты/input.txt","Результаты/encoded.txt")
    RLEFile.load_compressed("Результаты/encoded.txt", "Результаты/decoded.txt")
    print("\n")

def test_simpledata():
    print("---Тестирование простейших тестовых данных")
    print("\nРазные Ms")
    data_d_ms = bytes([0x12, 0x34, 0x12, 0x34, 0x12, 0x34])
    print(f"Исходные: {' '.join(f'0x{b:02X}' for b in data_d_ms)}")
    for Ms in [1, 2, 3]:
        encoded = RLE_encode(data_d_ms, Ms=Ms, Mc=1)
        decoded = RLE_decode(encoded, Ms=Ms, Mc=1)

        print("Ms=", Ms)
        print(f"Закодированные: {' '.join(f'0x{b:02X}' for b in encoded)}")
        print(f"Декодированные: {' '.join(f'0x{b:02X}' for b in decoded)}")

    print("\nКириллица UTF-8:")
    data4 = "TESTTT АааБББВВВГДЕКПП"
    encoded4, Ms = RLE_encode(data4, utf8=True)
    decoded4 = RLE_decode(encoded4, Ms=Ms, utf8=True)
    print(f"Исходные: '{data4}' (длина: {len(data4)})")
    print(f"Закодированные: {' '.join(f'0x{b:02X}' for b in encoded4)}")
    print(f"Декодированные: '{decoded4}'")
    print("\n")

def test_testdata():
    print("---Тестирование основного тестового набора")
    RLEFile.compress_file("Тестовые данные/Chehov_Anton__Bezotcovshina_www.Litmir.net_72436.txt", "Результаты/encoded.txt", utf8=True, is_text=True)
    print("\n")

    RLEFile.compress_file("Тестовые данные/enwik7", "Результаты/encoded.txt")
    print("\n")

    RLEFile.compress_file("Тестовые данные/RAW_bw.raw", "Результаты/encoded.txt")
    print("\n")

    RLEFile.compress_file("Тестовые данные/RAW_gray.raw", "Результаты/encoded.txt")
    print("\n")

    RLEFile.compress_file("Тестовые данные/RAW_color.raw", "Результаты/encoded.txt")
    print("\n")

    RLEFile.compress_file("Тестовые данные/nvidia-smi.exe", "Результаты/encoded.txt")
    print("\n")

# test_file()
# test_simpledata()
# test_testdata()
import struct
import os


class LZ77:
    def __init__(self, window_size=4096, lookahead_size=16):
        self.window_size = window_size
        self.lookahead_size = lookahead_size
        self.offset_bits = (window_size - 1).bit_length()
        self.length_bits = lookahead_size.bit_length()
        self.offset_bytes = (self.offset_bits + 7) // 8
        self.length_bytes = (self.length_bits + 7) // 8

    def encode(self, data):
        if not data:
            return b''

        n = len(data)
        pos = 0
        result = bytearray()

        while pos < n:
            match_offset = 0
            match_length = 0
            window_start = max(0, pos - self.window_size)
            window = data[window_start:pos]
            lookahead_end = min(pos + self.lookahead_size, n)
            lookahead = data[pos:lookahead_end]

            if window and lookahead:
                best_offset = 0
                best_length = 0
                for offset in range(1, min(len(window), self.window_size) + 1):
                    start_pos = len(window) - offset
                    length = 0
                    while (length < len(lookahead) and
                           start_pos + length < len(window) and
                           window[start_pos + length] == lookahead[length]):
                        length += 1
                    if length > best_length:
                        best_length = length
                        best_offset = offset
                        if best_length == self.lookahead_size:
                            break
                match_offset = best_offset
                match_length = best_length

            if match_length >= 2:
                result.append(0x01)
                result.extend(match_offset.to_bytes(self.offset_bytes, 'big'))
                result.extend(match_length.to_bytes(self.length_bytes, 'big'))
                pos += match_length
            else:
                result.append(0x00)
                result.append(data[pos])
                pos += 1
        return bytes(result)

    def decode(self, encoded_data):
        if not encoded_data:
            return b''
        result = bytearray()
        pos = 0
        n = len(encoded_data)
        while pos < n:
            if pos >= n:
                break
            flag = encoded_data[pos]
            pos += 1
            if flag == 0x00:
                if pos >= n:
                    break
                result.append(encoded_data[pos])
                pos += 1
            elif flag == 0x01:
                if pos + self.offset_bytes > n:
                    break
                offset = int.from_bytes(encoded_data[pos:pos + self.offset_bytes], 'big')
                pos += self.offset_bytes
                if pos + self.length_bytes > n:
                    break
                length = int.from_bytes(encoded_data[pos:pos + self.length_bytes], 'big')
                pos += self.length_bytes
                start = len(result) - offset
                if start < 0:
                    start = 0
                for i in range(length):
                    result.append(result[start + i])
        return bytes(result)

class LZSS:
    def __init__(self, window_size=4096, lookahead_size=16, min_match=3):
        self.window_size = window_size
        self.lookahead_size = lookahead_size
        self.min_match = min_match
        self.offset_bits = (window_size - 1).bit_length()
        self.length_bits = (lookahead_size - 1).bit_length()
        self.offset_bytes = (self.offset_bits + 7) // 8
        self.length_bytes = (self.length_bits + 7) // 8
        self.max_offset = (1 << (self.offset_bytes * 8)) - 1
        self.max_length = (1 << (self.length_bytes * 8)) - 1

    def encode(self, data):
        if not data:
            return b''
        n = len(data)
        pos = 0
        result = bytearray()
        while pos < n:
            flags_byte = 0
            elements = []
            for bit_pos in range(8):
                if pos >= n:
                    break
                match_offset = 0
                match_length = 0
                window_start = max(0, pos - self.window_size)
                window = data[window_start:pos]
                lookahead_end = min(pos + self.lookahead_size, n)
                lookahead = data[pos:lookahead_end]
                if len(lookahead) >= self.min_match and window:
                    best_offset = 0
                    best_length = 0
                    max_offset = min(len(window), self.window_size)
                    for offset in range(1, max_offset + 1):
                        start_pos = len(window) - offset
                        length = 0
                        while (length < len(lookahead) and
                               start_pos + length < len(window) and
                               window[start_pos + length] == lookahead[length]):
                            length += 1
                            if length >= self.lookahead_size:
                                break
                        if length > best_length:
                            best_length = length
                            best_offset = offset
                            if best_length == self.lookahead_size:
                                break
                    match_offset = best_offset
                    match_length = best_length

                if match_length >= self.min_match:
                    flags_byte |= (1 << bit_pos)
                    elements.append(('ref', match_offset, match_length))
                    pos += match_length
                else:
                    elements.append(('lit', data[pos]))
                    pos += 1

            result.append(flags_byte)
            for elem in elements:
                if elem[0] == 'lit':
                    result.append(elem[1])
                else:
                    _, offset, length = elem
                    result.extend(offset.to_bytes(self.offset_bytes, 'big'))
                    result.extend(length.to_bytes(self.length_bytes, 'big'))
        return bytes(result)

    def decode(self, encoded_data):
        if not encoded_data:
            return b''
        result = bytearray()
        pos = 0
        n = len(encoded_data)
        while pos < n:
            if pos >= n:
                break
            flags_byte = encoded_data[pos]
            pos += 1
            for bit_pos in range(8):
                if pos >= n:
                    break
                if (flags_byte >> bit_pos) & 1:
                    if pos + self.offset_bytes > n:
                        break
                    offset = int.from_bytes(encoded_data[pos:pos + self.offset_bytes], 'big')
                    pos += self.offset_bytes
                    if pos + self.length_bytes > n:
                        break
                    length = int.from_bytes(encoded_data[pos:pos + self.length_bytes], 'big')
                    pos += self.length_bytes
                    start = len(result) - offset
                    if start < 0:
                        start = 0
                    for i in range(length):
                        result.append(result[start + i])
                else:
                    result.append(encoded_data[pos])
                    pos += 1
        return bytes(result)

class LZSSFileHandler:
    MAGIC = b'LZS\x00'
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
    def save_compressed(data, filename, window_size=4096, lookahead_size=16, min_match=3):
        if isinstance(data, str):
            data = data.encode('utf-8')
            is_text = True
        else:
            is_text = False

        encoder = LZSS(window_size, lookahead_size, min_match)
        encoded = encoder.encode(data)

        with open(filename, 'wb') as f:
            f.write(LZSSFileHandler.MAGIC)
            f.write(bytes([1 if is_text else 0]))
            f.write(LZSSFileHandler.int_to_bytes(window_size, 4))
            f.write(LZSSFileHandler.int_to_bytes(lookahead_size, 4))
            f.write(LZSSFileHandler.int_to_bytes(min_match, 4))
            f.write(LZSSFileHandler.int_to_bytes(len(data), 8))
            f.write(LZSSFileHandler.int_to_bytes(len(encoded), 8))
            f.write(encoded)

        return len(encoded)

    @staticmethod
    def load_compressed(filename, decode_as_string=True):
        with open(filename, 'rb') as f:
            magic = f.read(4)
            if magic != LZSSFileHandler.MAGIC:
                raise ValueError(f"Неверный формат файла: {magic}")
            is_text = f.read(1)[0] == 1
            window_size = LZSSFileHandler.bytes_to_int(f.read(4))
            lookahead_size = LZSSFileHandler.bytes_to_int(f.read(4))
            min_match = LZSSFileHandler.bytes_to_int(f.read(4))
            original_size = LZSSFileHandler.bytes_to_int(f.read(8))
            encoded_size = LZSSFileHandler.bytes_to_int(f.read(8))
            encoded_data = f.read(encoded_size)
            if len(encoded_data) != encoded_size:
                raise ValueError(f"Неполные данные")
        decoder = LZSS(window_size, lookahead_size, min_match)
        decoded = decoder.decode(encoded_data)

        if len(decoded) > original_size:
            decoded = decoded[:original_size]
        if decode_as_string and is_text:
            return decoded.decode('utf-8')
        return decoded

    @staticmethod
    def compress_file(input_file, output_file, window_size=4096, lookahead_size=16, min_match=3, is_text_file=False):
        if is_text_file:
            with open(input_file, 'r', encoding='utf-8') as f:
                data = f.read()
        else:
            with open(input_file, 'rb') as f:
                data = f.read()
        encoded_size = LZSSFileHandler.save_compressed(data, output_file, window_size, lookahead_size, min_match)
        original_size = os.path.getsize(input_file)
        ratio = original_size / encoded_size if encoded_size > 0 else 0
        print(f"\nФайл: {input_file}")
        print(f"Исходный размер: {original_size:,} байт")
        print(f"Сжатый размер: {encoded_size:,} байт")
        print(f"Коэффициент: {ratio:.2f}x")
        return ratio
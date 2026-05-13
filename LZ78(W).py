import os
from typing import Tuple


class LZ78:
    def __init__(self, max_dict_size: int = 4096):
        self.max_dict_size = max_dict_size

    def encode(self, data: bytes) -> bytes:
        if not data:
            return b''
        dictionary = {}
        dict_size = 1
        result = bytearray()
        current_string = b''
        i = 0
        while i < len(data):
            byte = data[i:i + 1]
            if current_string + byte in dictionary:
                current_string += byte
            else:
                if current_string:
                    index = dictionary[current_string]
                else:
                    index = 0
                new_string = current_string + byte
                if dict_size < self.max_dict_size:
                    dictionary[new_string] = dict_size
                    dict_size += 1
                result.extend(self._encode_pair(index, byte))
                current_string = b''
            i += 1

        if current_string:
            last_byte = current_string[-1:]
            prefix = current_string[:-1]
            if prefix in dictionary:
                index = dictionary[prefix]
            else:
                index = 0
            result.extend(self._encode_pair(index, last_byte))
        return bytes(result)

    def decode(self, encoded_data: bytes) -> bytes:
        if not encoded_data:
            return b''
        dictionary = {}
        dict_size = 1
        result = bytearray()
        pos = 0
        pair_size = 4
        while pos < len(encoded_data):
            if pos + pair_size > len(encoded_data):
                break
            index, byte = self._decode_pair(encoded_data[pos:pos + pair_size])
            pos += pair_size
            if index == 0:
                string = byte
            else:
                if index in dictionary:
                    string = dictionary[index] + byte
                else:
                    continue
            if dict_size < self.max_dict_size:
                dictionary[dict_size] = string
                dict_size += 1
            result.extend(string)
        return bytes(result)

    def _encode_pair(self, index: int, byte: bytes) -> bytes:
        index_bytes = index.to_bytes(3, byteorder='big')
        return index_bytes + byte

    def _decode_pair(self, pair_bytes: bytes) -> Tuple[int, bytes]:
        index = int.from_bytes(pair_bytes[:3], byteorder='big')
        byte = pair_bytes[3:4]
        return index, byte

def lz78_encode(data: bytes, max_dict_size: int = 4096) -> bytes:
    encoder = LZ78(max_dict_size)
    return encoder.encode(data)

def lz78_decode(encoded_data: bytes, max_dict_size: int = 4096) -> bytes:
    decoder = LZ78(max_dict_size)
    return decoder.decode(encoded_data)

class LZW:
    def __init__(self, max_dict_size: int = 4096):
        self.max_dict_size = max_dict_size
        self.index_bytes = (max_dict_size.bit_length() + 7) // 8

    def _init_dict(self) -> dict:
        dictionary = {}
        for i in range(256):
            dictionary[bytes([i])] = i
        return dictionary

    def encode(self, data: bytes) -> bytes:
        if not data:
            return b''
        dictionary = self._init_dict()
        next_index = 256
        result = bytearray()
        current_string = b''

        for byte in data:
            current_byte = bytes([byte])
            new_string = current_string + current_byte
            if new_string in dictionary:
                current_string = new_string
            else:
                result.extend(dictionary[current_string].to_bytes(self.index_bytes, 'big'))
                if next_index < self.max_dict_size:
                    dictionary[new_string] = next_index
                    next_index += 1
                current_string = current_byte

        if current_string:
            result.extend(dictionary[current_string].to_bytes(self.index_bytes, 'big'))

        return bytes(result)

    def decode(self, encoded_data: bytes) -> bytes:
        if not encoded_data:
            return b''
        step = self.index_bytes
        n = len(encoded_data)
        dictionary = {}
        for i in range(256):
            dictionary[i] = bytes([i])
        next_index = 256
        if n < step:
            return b''

        pos = 0
        prev_index = int.from_bytes(encoded_data[pos:pos + step], 'big')
        pos += step
        result = bytearray(dictionary[prev_index])
        while pos + step <= n:
            current_index = int.from_bytes(encoded_data[pos:pos + step], 'big')
            pos += step
            if current_index in dictionary:
                current_string = dictionary[current_index]
            elif current_index == next_index:
                current_string = dictionary[prev_index] + bytes([dictionary[prev_index][0]])
            else:
                raise ValueError(f"Некорректный индекс: {current_index}")
            result.extend(current_string)
            if next_index < self.max_dict_size:
                new_string = dictionary[prev_index] + bytes([current_string[0]])
                dictionary[next_index] = new_string
                next_index += 1
            prev_index = current_index
        return bytes(result)

    def encode_with_stats(self, data: bytes) -> Tuple[bytes, dict]:
        if not data:
            return b'', {}

        dictionary = self._init_dict()
        next_index = 256
        result = bytearray()
        current_string = b''
        stats = {
            'original_size': len(data),
            'dict_size_init': 256,
            'dict_size_final': 256,
            'unique_codes': 0,
            'total_codes': 0
        }
        for byte in data:
            current_byte = bytes([byte])
            new_string = current_string + current_byte
            if new_string in dictionary:
                current_string = new_string
            else:
                result.extend(dictionary[current_string].to_bytes(self.index_bytes, 'big'))
                stats['total_codes'] += 1
                if next_index < self.max_dict_size:
                    dictionary[new_string] = next_index
                    next_index += 1
                    stats['unique_codes'] += 1
                current_string = current_byte

        if current_string:
            result.extend(dictionary[current_string].to_bytes(self.index_bytes, 'big'))
            stats['total_codes'] += 1
        stats['dict_size_final'] = next_index
        stats['compressed_size'] = len(result)
        stats['ratio'] = stats['original_size'] / stats['compressed_size'] if stats['compressed_size'] > 0 else 0
        return bytes(result), stats

class LZWFileHandler:
    MAGIC = b'LZW\x00'

    @staticmethod
    def int_to_bytes(value: int, size: int) -> bytes:
        result = bytearray()
        for i in range(size):
            result.append((value >> (i * 8)) & 0xFF)
        return bytes(result)

    @staticmethod
    def bytes_to_int(data: bytes) -> int:
        result = 0
        for i, byte in enumerate(data):
            result |= (byte << (i * 8))
        return result

    @staticmethod
    def save_compressed(data, filename: str, max_dict_size: int = 4096) -> int:
        if isinstance(data, str):
            data = data.encode('utf-8')
            is_text = True
        else:
            is_text = False
        encoder = LZW(max_dict_size)
        encoded = encoder.encode(data)

        with open(filename, 'wb') as f:
            f.write(LZWFileHandler.MAGIC)
            f.write(bytes([1 if is_text else 0]))
            f.write(LZWFileHandler.int_to_bytes(max_dict_size, 4))
            index_bytes = (max_dict_size.bit_length() + 7) // 8
            f.write(bytes([index_bytes]))
            f.write(LZWFileHandler.int_to_bytes(len(data), 8))
            f.write(LZWFileHandler.int_to_bytes(len(encoded), 8))
            f.write(encoded)

        print(f"Сжатые данные сохранены в: {filename}")
        print(f"Исходный размер: {len(data):,} байт")
        print(f"Сжатый размер: {len(encoded):,} байт")
        print(f"Коэффициент: {len(data) / len(encoded):.2f}x")
        print(f"Размер словаря: {max_dict_size}, индекс: {index_bytes} байт")
        return len(encoded)

    @staticmethod
    def load_compressed(filename: str, decode_as_string: bool = True):
        with open(filename, 'rb') as f:
            magic = f.read(4)
            if magic != LZWFileHandler.MAGIC:
                raise ValueError(f"Неверный формат файла: {magic}")

            is_text = f.read(1)[0] == 1
            max_dict_size_bytes = f.read(4)
            max_dict_size = LZWFileHandler.bytes_to_int(max_dict_size_bytes)
            index_bytes = f.read(1)[0]
            original_size_bytes = f.read(8)
            original_size = LZWFileHandler.bytes_to_int(original_size_bytes)
            encoded_size_bytes = f.read(8)
            encoded_size = LZWFileHandler.bytes_to_int(encoded_size_bytes)
            encoded_data = f.read(encoded_size)
            if len(encoded_data) != encoded_size:
                raise ValueError(f"Неполные данные: ожидалось {encoded_size}, получено {len(encoded_data)}")

        temp_encoder = LZW(max_dict_size)
        decoded = temp_encoder.decode(encoded_data)
        if len(decoded) > original_size:
            decoded = decoded[:original_size]
        if decode_as_string and is_text:
            return decoded.decode('utf-8')
        return decoded

    @staticmethod
    def compress_file(input_file: str, output_file: str, max_dict_size: int = 4096, is_text_file: bool = False) -> float:
        if is_text_file:
            with open(input_file, 'r', encoding='utf-8') as f:
                data = f.read()
        else:
            with open(input_file, 'rb') as f:
                data = f.read()

        encoded_size = LZWFileHandler.save_compressed(data, output_file, max_dict_size)
        original_size = os.path.getsize(input_file)
        ratio = original_size / encoded_size if encoded_size > 0 else 0
        print(f"\nФайл: {input_file}")
        print(f"Исходный размер: {original_size:,} байт")
        print(f"Сжатый размер: {encoded_size:,} байт")
        print(f"Коэффициент сжатия: {ratio:.2f}x")
        return ratio

    @staticmethod
    def decompress_file(input_file: str, output_file: str) -> None:
        decoded = LZWFileHandler.load_compressed(input_file, decode_as_string=False)
        with open(output_file, 'wb') as f:
            f.write(decoded)
        print(f"Распакованные данные сохранены в: {output_file}")
        print(f"Размер: {len(decoded):,} байт")

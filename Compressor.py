import os
import sys
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from RLE import RLEFile
from huffman import HuffmanFile
from BWT_RLE import BWTFileProcessor
from entropy import mtf_encode, mtf_decode
from huffman import HuffmanCoder
from BWT import bwt_encode_large_with_metadata, bwt_decode_large_with_metadata
from LZ77_SS import LZSS, LZSSFileHandler
from LZ78_W import LZW, LZWFileHandler


class HACompressor:
    @staticmethod
    def compress_file(input_file, output_file, is_text_file=False):
        HuffmanFile.compress_file(input_file, output_file)
        with open(input_file, 'rb') as f:
            original_size = len(f.read())
        compressed_size = os.path.getsize(output_file)
        return compressed_size, original_size

    @staticmethod
    def decompress_file(input_file, output_file):
        HuffmanFile.decompress_file(input_file, output_file, decode_as_string=False)
        return True


class RLECompressor:
    @staticmethod
    def compress_file(input_file, output_file, is_text_file=False):
        RLEFile.compress_file(input_file, output_file, Ms=1, Mc=1, utf8=False, is_text=is_text_file)
        with open(input_file, 'rb') as f:
            original_size = len(f.read())
        compressed_size = os.path.getsize(output_file)
        return compressed_size, original_size

    @staticmethod
    def decompress_file(input_file, output_file):
        RLEFile.load_compressed(input_file, output_file, decode_str=False)
        return True


class BWT_RLE_Compressor:
    BLOCK_SIZE = 1024

    @staticmethod
    def compress_file(input_file, output_file, is_text_file=False):
        ratio = BWTFileProcessor.compress_file_with_bwt(input_file, output_file,
                                                        block_size=BWT_RLE_Compressor.BLOCK_SIZE)
        with open(input_file, 'rb') as f:
            original_size = len(f.read())
        compressed_size = os.path.getsize(output_file)
        return compressed_size, original_size

    @staticmethod
    def decompress_file(input_file, output_file):
        BWTFileProcessor.decompress_file_with_bwt(input_file, output_file)
        return True


class BWT_MTF_HA_Compressor:
    BLOCK_SIZE = 1024

    @staticmethod
    def compress_file(input_file, output_file, is_text_file=False):
        # Читаем файл
        if is_text_file:
            with open(input_file, 'r', encoding='utf-8') as f:
                data = f.read().encode('utf-8')
        else:
            with open(input_file, 'rb') as f:
                data = f.read()

        original_size = len(data)

        bwt_package, _ = bwt_encode_large_with_metadata(data, BWT_MTF_HA_Compressor.BLOCK_SIZE)

        mtf_result = mtf_encode(bwt_package)

        encoded, code_lengths, _ = HuffmanCoder.encode(mtf_result)

        with open(output_file, 'wb') as f:
            f.write(b'BMH\x00')
            f.write(bytes([1 if is_text_file else 0]))
            non_zero = {k: v for k, v in code_lengths.items() if v > 0}
            f.write(len(non_zero).to_bytes(2, 'little'))
            for sym, length in non_zero.items():
                f.write(bytes([sym]))
                f.write(bytes([length]))
            f.write(len(encoded).to_bytes(8, 'little'))
            f.write(encoded)

        return len(encoded), original_size

    @staticmethod
    def decompress_file(input_file, output_file):
        with open(input_file, 'rb') as f:
            magic = f.read(4)
            if magic != b'BMH\x00':
                raise ValueError("Неверный формат")
            is_text = f.read(1)[0] == 1
            num_symbols = int.from_bytes(f.read(2), 'little')
            code_lengths = {}
            for _ in range(num_symbols):
                sym = f.read(1)[0]
                length = f.read(1)[0]
                code_lengths[sym] = length
            encoded_size = int.from_bytes(f.read(8), 'little')
            encoded = f.read(encoded_size)

        mtf_result = HuffmanCoder.decode(encoded, code_lengths)
        bwt_package = mtf_decode(mtf_result)
        decoded = bwt_decode_large_with_metadata(bwt_package)

        with open(output_file, 'wb') as f:
            f.write(decoded)

        return True


class BWT_MTF_RLE_HA_Compressor:
    BLOCK_SIZE = 1024

    @staticmethod
    def compress_file(input_file, output_file, is_text_file=False):
        if is_text_file:
            with open(input_file, 'r', encoding='utf-8') as f:
                data = f.read().encode('utf-8')
        else:
            with open(input_file, 'rb') as f:
                data = f.read()

        original_size = len(data)

        bwt_package, _ = bwt_encode_large_with_metadata(data, BWT_MTF_RLE_HA_Compressor.BLOCK_SIZE)

        mtf_result = mtf_encode(bwt_package)

        from RLE import RLE_encode
        rle_result = RLE_encode(mtf_result, Ms=1, Mc=1)

        encoded, code_lengths, _ = HuffmanCoder.encode(rle_result)

        with open(output_file, 'wb') as f:
            f.write(b'BMR\x00')
            f.write(bytes([1 if is_text_file else 0]))
            non_zero = {k: v for k, v in code_lengths.items() if v > 0}
            f.write(len(non_zero).to_bytes(2, 'little'))
            for sym, length in non_zero.items():
                f.write(bytes([sym]))
                f.write(bytes([length]))
            f.write(len(encoded).to_bytes(8, 'little'))
            f.write(encoded)

        return len(encoded), original_size

    @staticmethod
    def decompress_file(input_file, output_file):
        with open(input_file, 'rb') as f:
            magic = f.read(4)
            if magic != b'BMR\x00':
                raise ValueError("Неверный формат")
            is_text = f.read(1)[0] == 1
            num_symbols = int.from_bytes(f.read(2), 'little')
            code_lengths = {}
            for _ in range(num_symbols):
                sym = f.read(1)[0]
                length = f.read(1)[0]
                code_lengths[sym] = length
            encoded_size = int.from_bytes(f.read(8), 'little')
            encoded = f.read(encoded_size)

        rle_result = HuffmanCoder.decode(encoded, code_lengths)
        from RLE import RLE_decode
        mtf_result = RLE_decode(rle_result, Ms=1, Mc=1)
        bwt_package = mtf_decode(mtf_result)
        decoded = bwt_decode_large_with_metadata(bwt_package)

        with open(output_file, 'wb') as f:
            f.write(decoded)

        return True


class LZSSCompressor:
    WINDOW_SIZE = 512
    LOOKAHEAD_SIZE = 16
    MIN_MATCH = 3

    @staticmethod
    def compress_file(input_file, output_file, is_text_file=False):
        LZSSFileHandler.compress_file(input_file, output_file,
                                      window_size=LZSSCompressor.WINDOW_SIZE,
                                      lookahead_size=LZSSCompressor.LOOKAHEAD_SIZE,
                                      min_match=LZSSCompressor.MIN_MATCH,
                                      is_text_file=is_text_file)
        with open(input_file, 'rb') as f:
            original_size = len(f.read())
        compressed_size = os.path.getsize(output_file)
        return compressed_size, original_size

    @staticmethod
    def decompress_file(input_file, output_file):
        LZSSFileHandler.load_compressed(input_file, decode_as_string=False)
        with open(input_file, 'rb') as f:
            magic = f.read(4)
            if magic != LZSSFileHandler.MAGIC:
                raise ValueError("Неверный формат")
            f.seek(0)
            decoded = LZSSFileHandler.load_compressed(input_file, decode_as_string=False)
            with open(output_file, 'wb') as out:
                out.write(decoded)
        return True


class LZSS_HA_Compressor:
    WINDOW_SIZE = 512
    LOOKAHEAD_SIZE = 16
    MIN_MATCH = 3

    @staticmethod
    def compress_file(input_file, output_file, is_text_file=False):
        if is_text_file:
            with open(input_file, 'r', encoding='utf-8') as f:
                data = f.read().encode('utf-8')
        else:
            with open(input_file, 'rb') as f:
                data = f.read()

        original_size = len(data)

        encoder = LZSS(window_size=LZSS_HA_Compressor.WINDOW_SIZE,
                       lookahead_size=LZSS_HA_Compressor.LOOKAHEAD_SIZE,
                       min_match=LZSS_HA_Compressor.MIN_MATCH)
        lzss_result = encoder.encode(data)

        encoded, code_lengths, _ = HuffmanCoder.encode(lzss_result)

        with open(output_file, 'wb') as f:
            f.write(b'LH\x00')
            f.write(bytes([1 if is_text_file else 0]))
            non_zero = {k: v for k, v in code_lengths.items() if v > 0}
            f.write(len(non_zero).to_bytes(2, 'little'))
            for sym, length in non_zero.items():
                f.write(bytes([sym]))
                f.write(bytes([length]))
            f.write(len(encoded).to_bytes(8, 'little'))
            f.write(encoded)

        return len(encoded), original_size

    @staticmethod
    def decompress_file(input_file, output_file):
        with open(input_file, 'rb') as f:
            magic = f.read(3)
            if magic != b'LH\x00':
                raise ValueError("Неверный формат")
            is_text = f.read(1)[0] == 1
            num_symbols = int.from_bytes(f.read(2), 'little')
            code_lengths = {}
            for _ in range(num_symbols):
                sym = f.read(1)[0]
                length = f.read(1)[0]
                code_lengths[sym] = length
            encoded_size = int.from_bytes(f.read(8), 'little')
            encoded = f.read(encoded_size)

        lzss_result = HuffmanCoder.decode(encoded, code_lengths)
        decoder = LZSS(window_size=LZSS_HA_Compressor.WINDOW_SIZE,
                       lookahead_size=LZSS_HA_Compressor.LOOKAHEAD_SIZE,
                       min_match=LZSS_HA_Compressor.MIN_MATCH)
        decoded = decoder.decode(lzss_result)

        with open(output_file, 'wb') as f:
            f.write(decoded)

        return True


class LZWCompressor:
    MAX_DICT_SIZE = 65536

    @staticmethod
    def compress_file(input_file, output_file, is_text_file=False):
        LZWFileHandler.compress_file(input_file, output_file,
                                     max_dict_size=LZWCompressor.MAX_DICT_SIZE,
                                     is_text_file=is_text_file)
        with open(input_file, 'rb') as f:
            original_size = len(f.read())
        compressed_size = os.path.getsize(output_file)
        return compressed_size, original_size

    @staticmethod
    def decompress_file(input_file, output_file):
        LZWFileHandler.decompress_file(input_file, output_file)
        return True


class LZW_HA_Compressor:
    MAX_DICT_SIZE = 65536

    @staticmethod
    def compress_file(input_file, output_file, is_text_file=False):
        if is_text_file:
            with open(input_file, 'r', encoding='utf-8') as f:
                data = f.read().encode('utf-8')
        else:
            with open(input_file, 'rb') as f:
                data = f.read()

        original_size = len(data)

        encoder = LZW(max_dict_size=LZW_HA_Compressor.MAX_DICT_SIZE)
        lzw_result = encoder.encode(data)

        encoded, code_lengths, _ = HuffmanCoder.encode(lzw_result)

        with open(output_file, 'wb') as f:
            f.write(b'LW\x01')
            f.write(bytes([1 if is_text_file else 0]))
            f.write(LZW_HA_Compressor.MAX_DICT_SIZE.to_bytes(4, 'little'))
            non_zero = {k: v for k, v in code_lengths.items() if v > 0}
            f.write(len(non_zero).to_bytes(2, 'little'))
            for sym, length in non_zero.items():
                f.write(bytes([sym]))
                f.write(bytes([length]))
            f.write(len(encoded).to_bytes(8, 'little'))
            f.write(encoded)

        return len(encoded), original_size

    @staticmethod
    def decompress_file(input_file, output_file):
        with open(input_file, 'rb') as f:
            magic = f.read(3)
            if magic != b'LW\x01':
                raise ValueError("Неверный формат")
            is_text = f.read(1)[0] == 1
            max_dict_size = int.from_bytes(f.read(4), 'little')
            num_symbols = int.from_bytes(f.read(2), 'little')
            code_lengths = {}
            for _ in range(num_symbols):
                sym = f.read(1)[0]
                length = f.read(1)[0]
                code_lengths[sym] = length
            encoded_size = int.from_bytes(f.read(8), 'little')
            encoded = f.read(encoded_size)

        lzw_result = HuffmanCoder.decode(encoded, code_lengths)
        decoder = LZW(max_dict_size=max_dict_size)
        decoded = decoder.decode(lzw_result)

        with open(output_file, 'wb') as f:
            f.write(decoded)

        return True


# Компрессор

TEST_FILES = [
    ("Chehov_Anton__Bezotcovshina_www.Litmir.net_72436.txt", True),
    ("RAW_bw.raw", False),
    ("RAW_gray.raw", False),
    ("RAW_color.raw", False),
    ("nvidia-smi.exe", False),
]

COMPRESSORS = {
    "1": {
        "name": "HA (Хаффман)",
        "compress_class": HACompressor,
        "suffix": ".ha"
    },
    "2": {
        "name": "RLE",
        "compress_class": RLECompressor,
        "suffix": ".rle"
    },
    "3": {
        "name": "BWT + RLE",
        "compress_class": BWT_RLE_Compressor,
        "suffix": ".bwt_rle"
    },
    "4": {
        "name": "BWT + MTF + HA",
        "compress_class": BWT_MTF_HA_Compressor,
        "suffix": ".bmt_h"
    },
    "5": {
        "name": "BWT + MTF + RLE + HA",
        "compress_class": BWT_MTF_RLE_HA_Compressor,
        "suffix": ".bmt_r_h"
    },
    "6": {
        "name": "LZSS",
        "compress_class": LZSSCompressor,
        "suffix": ".lzss"
    },
    "7": {
        "name": "LZSS + HA",
        "compress_class": LZSS_HA_Compressor,
        "suffix": ".lzss_ha"
    },
    "8": {
        "name": "LZW",
        "compress_class": LZWCompressor,
        "suffix": ".lzw"
    },
    "9": {
        "name": "LZW + HA",
        "compress_class": LZW_HA_Compressor,
        "suffix": ".lzw_ha"
    }
}

def print_menu():
    print("\nВыберите компрессор:")
    for key, info in COMPRESSORS.items():
        print(f"  {key}. {info['name']}")
    print("\n  0. Выйти")


def run_compressor(choice):
    if choice not in COMPRESSORS:
        print("Неверный выбор!")
        return

    compressor_info = COMPRESSORS[choice]
    compressor_name = compressor_info["name"]
    compress_class = compressor_info["compress_class"]
    suffix = compressor_info["suffix"]
    print(f"Сжатие: {compressor_name}")

    results = []

    for filename, is_text in TEST_FILES:
        input_path = os.path.join("Тестовые данные", filename)

        if not os.path.exists(input_path):
            print(f"\nФайл не найден: {input_path}")
            continue

        base_name = os.path.splitext(filename)[0]
        compressed_path = os.path.join("Результаты/compressed", f"{base_name}{suffix}")
        decompressed_path = os.path.join("Результаты/decompressed",
                                         f"{base_name}_decoded{os.path.splitext(filename)[1]}")

        print(f"\nОбработка: {filename}")

        try:
            start_time = time.time()
            compressed_size, original_size = compress_class.compress_file(
                input_path, compressed_path, is_text_file=is_text
            )
            compress_time = time.time() - start_time

            start_time = time.time()
            compress_class.decompress_file(compressed_path, decompressed_path)
            decompress_time = time.time() - start_time

            with open(input_path, 'rb') as f:
                original_data = f.read()
            with open(decompressed_path, 'rb') as f:
                decompressed_data = f.read()

            ratio = original_size / compressed_size if compressed_size > 0 else 0
            savings = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
            results.append({
                'file': filename,
                'original': original_size,
                'compressed': compressed_size,
                'ratio': ratio,
                'savings': savings,
                'compress_time': compress_time,
                'decompress_time': decompress_time
            })

            print(f"  Исходный размер: {original_size:,} байт")
            print(f"  Сжатый размер: {compressed_size:,} байт")
            print(f"  Коэффициент сжатия: {ratio:.2f}x")
            print(f"  Экономия: {savings:.1f}%")
            print(f"  Время сжатия: {compress_time:.3f} сек")
            print(f"  Время декомпрессии: {decompress_time:.3f} сек")

        except Exception as e:
            print(f"  Ошибка: {e}")
            import traceback
            traceback.print_exc()

    if results:
        print(f"Результаты - {compressor_name}")
        print(f"{'Файл':<55} {'Исходный':>12} {'Сжатый':>12} {'Коэфф':>8} {'%':>6} {'Статус':>8}")

        total_original = 0
        total_compressed = 0

        for r in results:
            total_original += r['original']
            total_compressed += r['compressed']
            print(
                f"{r['file']:<55} {r['original']:>12,} {r['compressed']:>12,} {r['ratio']:>7.2f}x {r['savings']:>5.1f}%")
        total_ratio = total_original / total_compressed if total_compressed > 0 else 0
        total_savings = (1 - total_compressed / total_original) * 100
    print(f"Результаты сохранены в:")
    print(f"Сжатые файлы: Результаты/compressed/")
    print(f"Декомпрессированные: Результаты/decompressed/")

while True:
    print_menu()
    choice = input("\nВаш выбор: ").strip()
    if choice == "0":
        print("До свидания!")
        break
    run_compressor(choice)
    input("\nНажмите Enter для продолжения")

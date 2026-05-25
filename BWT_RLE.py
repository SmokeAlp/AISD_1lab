import os
from BWT import bwt_encode_large, bwt_decode_large, bwt_encode_large_with_metadata, bwt_decode_large_with_metadata
from RLE import RLE_encode, RLEFile, RLE_decode


class BWTFileProcessor:
    @staticmethod
    def compress_file_with_bwt(input_file, output_file, block_size=4096):
        with open(input_file, 'rb') as f:
            data = f.read()

        original_size = len(data)
        print(f"\n--Обработка файла: {input_file}")
        print(f"Исходный размер: {original_size:,} байт")
        print(f"Размер блока: {block_size} байт")

        bwt_package, num_blocks = bwt_encode_large_with_metadata(data, block_size)
        rle_data = RLE_encode(bwt_package, Ms=1, Mc=1)

        with open(output_file, 'wb') as f:
            f.write(b'BWT\x00')
            f.write(rle_data)

        compressed_size = os.path.getsize(output_file)
        ratio = original_size / compressed_size if compressed_size > 0 else 0
        print(f"Сжатый файл: {compressed_size:,} байт")
        print(f"Коэффициент сжатия: {ratio:.2f}x")
        return ratio

    @staticmethod
    def decompress_file_with_bwt(input_file, output_file):
        with open(input_file, 'rb') as f:
            magic = f.read(4)
            if magic != b'BWT\x00':
                raise ValueError(f"Неверный формат: {magic}")
            rle_data = f.read()

        print(f"\nРаспаковка файла: {input_file}")
        bwt_package = RLE_decode(rle_data, Ms=1, Mc=1)
        decoded_data = bwt_decode_large_with_metadata(bwt_package)

        with open(output_file, 'wb') as f:
            f.write(decoded_data)
        print(f"Распакованные данные сохранены в: {output_file}")
        print(f"Размер: {len(decoded_data):,} байт")
        return decoded_data

def compress_all_test_files():
    print("---Сжатие BWT + RLE")

    test_files = [("Тестовые данные/Chehov_Anton__Bezotcovshina_www.Litmir.net_72436.txt", "Текст"),
        ("Тестовые данные/enwik7", "enwik7"),
        ("Тестовые данные/RAW_bw.raw", "Черно-белое изображение"),
        ("Тестовые данные/RAW_gray.raw", "Оттенки серого"),
        ("Тестовые данные/RAW_color.raw", "Цветное изображение"),
        ("Тестовые данные/nvidia-smi.exe", "Исполняемый файл"),]
    output_files = ["Результаты/BWT_RLE_Chehov_Anton__Bezotcovshina_www.Litmir.net_72436.txt",
                    "Результаты/BWT_RLE_enwik7", "Результаты/BWT_RLE_RAW_bw.raw", "Результаты/BWT_RLE_RAW_gray.raw",
                    "Результаты/BWT_RLE_RAW_color.raw", "Результаты/BWT_RLE_nvidia-smi.exe"]
    i = 0
    results = {}

    for file_path, description in test_files:
        if not os.path.exists(file_path):
            print(f"\nФайл не найден: {file_path}")
            continue
        output_file = output_files[i] + ".bwt_rle"
        try:
            ratio = BWTFileProcessor.compress_file_with_bwt(file_path, output_file, block_size=4096)
            results[description] = ratio
            decompressed_file = output_files[i] + ".bwt_rle.dec"
            BWTFileProcessor.decompress_file_with_bwt(output_file, decompressed_file)
        except Exception as e:
            print(f"Ошибка при сжатии: {e}")
        i += 1

    print("Коэффициенты сжатия:")
    for name, ratio in results.items():
        print(f"  {name}: {ratio:.2f}x")

# compress_all_test_files()
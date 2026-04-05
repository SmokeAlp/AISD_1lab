from PIL import Image

def convert(input_path, output_path, type):
    with Image.open(input_path) as img:
        width, height = img.size

        if type == 'bw':
            converted = img.convert('1')
            img_type = 0x01
        elif type == 'gray':
            converted = img.convert('L')
            img_type = 0x02
        else:
            converted = img.convert('RGB')
            img_type = 0x03
        pixel_data = converted.tobytes()
        header = bytearray(4)
        header[0] = 0xAB
        header[1] = img_type
        header[2] = width & 0xFF
        header[3] = (width >> 8) & 0xFF

        with open(output_path, 'wb') as f:
            f.write(header)
            f.write(pixel_data)


def read_raw_file(raw_file):
    with open(raw_file, 'rb') as f:
        header = f.read(4)

        magic = header[0]
        img_type = header[1]
        width = header[2] | (header[3] << 8)

        type_names = {0x01: "Чб",
                      0x02: "Оттенки серого",
                      0x03: "Цветное"}

        print(f"Файл: {raw_file}")
        print(f"  0x{magic:02X}")
        print(f"  {type_names.get(img_type)}")
        pixel_data = f.read()
        print(f"  Размер данных: {len(pixel_data):,} байт")

# convert("Тестовые данные/bw.jpg", "Тестовые данные/RAW_bw.raw", "bw")
# convert("Тестовые данные/gray.jpg", "Тестовые данные/RAW_gray.raw", "gray")
# convert("Тестовые данные/color.jpg", "Тестовые данные/RAW_color.raw", "color")

read_raw_file("Тестовые данные/RAW_bw.raw")
read_raw_file("Тестовые данные/RAW_gray.raw")
read_raw_file("Тестовые данные/RAW_color.raw")
import io
from urllib.request import Request, urlopen

from PIL import Image


pebble_palette = [
    (0, 0, 0),
    (0, 0, 85),
    (0, 0, 170),
    (0, 0, 255),
    (0, 85, 0),
    (0, 85, 85),
    (0, 85, 170),
    (0, 85, 255),
    (0, 170, 0),
    (0, 170, 85),
    (0, 170, 170),
    (0, 170, 255),
    (0, 255, 0),
    (0, 255, 85),
    (0, 255, 170),
    (0, 255, 255),
    (85, 0, 0),
    (85, 0, 85),
    (85, 0, 170),
    (85, 0, 255),
    (85, 85, 0),
    (85, 85, 85),
    (85, 85, 170),
    (85, 85, 255),
    (85, 170, 0),
    (85, 170, 85),
    (85, 170, 170),
    (85, 170, 255),
    (85, 255, 0),
    (85, 255, 85),
    (85, 255, 170),
    (85, 255, 255),
    (170, 0, 0),
    (170, 0, 85),
    (170, 0, 170),
    (170, 0, 255),
    (170, 85, 0),
    (170, 85, 85),
    (170, 85, 170),
    (170, 85, 255),
    (170, 170, 0),
    (170, 170, 85),
    (170, 170, 170),
    (170, 170, 255),
    (170, 255, 0),
    (170, 255, 85),
    (170, 255, 170),
    (170, 255, 255),
    (255, 0, 0),
    (255, 0, 85),
    (255, 0, 170),
    (255, 0, 255),
    (255, 85, 0),
    (255, 85, 85),
    (255, 85, 170),
    (255, 85, 255),
    (255, 170, 0),
    (255, 170, 85),
    (255, 170, 170),
    (255, 170, 255),
    (255, 255, 0),
    (255, 255, 85),
    (255, 255, 170),
    (255, 255, 255)
]
pebble_palette = [color for item in pebble_palette for color in item]

palette_image = Image.frombytes(
    mode='RGB',
    size=(64, 1),
    data=bytes(pebble_palette)
).convert('P')

max_size = (144, 168)


def download(url):
    r = Request(url, headers={'User-Agent': 'Wget/1.16.3 (darwin14.1.0)'})
    return urlopen(r).read()


def convert_to_png64(image_data,
        width=None,
        height=None,
        ratio=None):
    if ratio and (width or height):
        raise ValueError("Specify either `ratio` or size")

    image = Image.open(io.BytesIO(image_data))

    new_size = None

    if width and height:
        new_size = (width, height)
    elif width:
        ratio = width/image.size[0]
    elif height:
        ratio = height/image.size[1]
    elif ratio is None:
        ratio = min(max_size[i]/image.size[i] for i in (0, 1))

    if not new_size:
        new_size = tuple(round(axis * ratio) for axis in image.size)

    image = Image.open(io.BytesIO(image_data))
    image.thumbnail(new_size)

    converted = image.convert(
        mode='P',
        palette=palette_image,
    ).convert(mode='RGB')

    out = io.BytesIO()
    converted.save(out, format='png')
    out.seek(0)
    return out.read()


def download_and_convert_to_png64(url, *args, **kwargs):
    downloaded_data = download(url)

    return convert_to_png64(downloaded_data, *args, **kwargs)

if __name__ == "__main__":
    import sys
    with io.open(sys.argv[2], 'wb') as out_f:
        out_f.write(download_and_convert_to_png64(sys.argv[1]))

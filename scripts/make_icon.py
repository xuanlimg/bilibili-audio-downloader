"""生成 Windows 软件图标。"""

from pathlib import Path

from PIL import Image, ImageDraw


def main() -> None:
    size = 1024
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    gradient = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    pixels = gradient.load()
    for y in range(size):
        ratio = y / (size - 1)
        red = int(21 + (22 - 21) * ratio)
        green = int(59 + (119 - 59) * ratio)
        blue = int(91 + (255 - 91) * ratio)
        for x in range(size):
            pixels[x, y] = (red, green, blue, 255)

    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle((34, 34, size - 34, size - 34), radius=210, fill=255)
    image.paste(gradient, (0, 0), mask)

    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (34, 34, size - 34, size - 34),
        radius=210,
        outline=(255, 255, 255, 42),
        width=10,
    )
    draw.arc((210, 205, 814, 825), start=182, end=358, fill=(255, 255, 255, 245), width=76)
    draw.rounded_rectangle((178, 520, 306, 754), radius=62, fill=(255, 255, 255, 245))
    draw.rounded_rectangle((718, 520, 846, 754), radius=62, fill=(255, 255, 255, 245))
    draw.rounded_rectangle((208, 596, 278, 752), radius=35, fill=(251, 114, 153, 255))
    draw.rounded_rectangle((746, 596, 816, 752), radius=35, fill=(251, 114, 153, 255))
    draw.polygon([(438, 425), (438, 675), (670, 550)], fill=(255, 255, 255, 255))

    assets = Path(__file__).resolve().parent.parent / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    image.resize((256, 256), Image.Resampling.LANCZOS).save(assets / "app.png")
    image.save(
        assets / "app.ico",
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )


if __name__ == "__main__":
    main()

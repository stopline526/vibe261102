"""앱 아이콘(app.ico) 생성: GUI 배너와 같은 파랑→보라 그라데이션 위에 상승 라인 차트 모양"""

from PIL import Image, ImageDraw

SIZE = 256


def make_icon(path: str = "app.ico") -> None:
    # 파랑(#1d4ed8) → 보라(#7c3aed) 대각선 그라데이션
    gradient = Image.new("RGBA", (SIZE, SIZE))
    start, end = (0x1D, 0x4E, 0xD8), (0x7C, 0x3A, 0xED)
    for y in range(SIZE):
        for x in range(SIZE):
            t = (x + y) / (2 * (SIZE - 1))
            gradient.putpixel((x, y), tuple(int(s + (e - s) * t) for s, e in zip(start, end)) + (255,))

    # 둥근 사각형 모양으로 자르기
    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, SIZE - 1, SIZE - 1), radius=56, fill=255)
    icon = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    icon.paste(gradient, mask=mask)

    # 반투명 면적 + 흰색 꺾은선: 하락 후 크게 반등하는 지수 모양
    points = [(40, 120), (78, 96), (112, 150), (146, 128), (180, 104), (216, 52)]
    layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    ImageDraw.Draw(layer).polygon(points + [(216, 212), (40, 212)], fill=(255, 255, 255, 70))
    icon = Image.alpha_composite(icon, layer)
    draw = ImageDraw.Draw(icon)
    draw.line([(40, 212), (216, 212)], fill="white", width=6)
    draw.line(points, fill="white", width=14, joint="curve")
    x, y = points[-1]
    draw.ellipse((x - 14, y - 14, x + 14, y + 14), fill="white")

    icon.save(path, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(f"아이콘 생성 완료: {path}")


if __name__ == "__main__":
    make_icon()

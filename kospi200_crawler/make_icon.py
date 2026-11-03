"""앱 아이콘(app.ico) 생성: GUI 배너와 같은 파랑→보라 그라데이션 위에 상승 차트 모양"""

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

    # 흰색 막대 차트 + 빨간 상승 꺾은선
    draw = ImageDraw.Draw(icon)
    for x, top in ((56, 150), (98, 120), (140, 136), (182, 92)):
        draw.rounded_rectangle((x, top, x + 26, 200), radius=6, fill="white")
    points = [(69, 128), (111, 96), (153, 112), (195, 62)]
    draw.line(points, fill="#f87171", width=12, joint="curve")
    for x, y in points:
        draw.ellipse((x - 10, y - 10, x + 10, y + 10), fill="#f87171")

    icon.save(path, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(f"아이콘 생성 완료: {path}")


if __name__ == "__main__":
    make_icon()

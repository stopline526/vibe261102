"""앱 아이콘(app.ico) 생성: GUI 배너와 같은 보라→핑크 그라데이션 위에 신문 모양"""

from PIL import Image, ImageDraw

SIZE = 256


def make_icon(path: str = "app.ico") -> None:
    # 보라(#6366f1) → 핑크(#ec4899) 대각선 그라데이션
    gradient = Image.new("RGBA", (SIZE, SIZE))
    start, end = (0x63, 0x66, 0xF1), (0xEC, 0x48, 0x99)
    for y in range(SIZE):
        for x in range(SIZE):
            t = (x + y) / (2 * (SIZE - 1))
            gradient.putpixel((x, y), tuple(int(s + (e - s) * t) for s, e in zip(start, end)) + (255,))

    # 둥근 사각형 모양으로 자르기
    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, SIZE - 1, SIZE - 1), radius=56, fill=255)
    icon = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    icon.paste(gradient, mask=mask)

    # 흰색 신문: 종이, 사진 영역, 기사 줄
    draw = ImageDraw.Draw(icon)
    draw.rounded_rectangle((52, 60, 204, 196), radius=14, fill="white")
    draw.rounded_rectangle((70, 80, 186, 96), radius=6, fill="#a855f7")
    draw.rounded_rectangle((70, 110, 120, 160), radius=6, fill="#ec4899")
    for y in (112, 128, 144, 160):
        draw.rounded_rectangle((132, y, 186, y + 7), radius=3, fill="#94a3b8")
    draw.rounded_rectangle((70, 172, 186, 179), radius=3, fill="#94a3b8")

    icon.save(path, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(f"아이콘 생성 완료: {path}")


if __name__ == "__main__":
    make_icon()

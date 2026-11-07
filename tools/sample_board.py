"""Compose screenshots into a captioned board (docs/img/*.png).

    python3 tools/sample_board.py out.png "Title" img1:caption1 img2:caption2 ...
Images are laid out 2 per row at 800 px wide each, with the game's palette.
"""
import sys
from PIL import Image, ImageDraw, ImageFont

FONT = 'game/assets/fonts/Fredoka.ttf'
BG = (255, 247, 230)
INK = (74, 52, 38)
PINK = (226, 87, 122)


def main():
    out, title, items = sys.argv[1], sys.argv[2], sys.argv[3:]
    W, pad, cap = 800, 24, 46
    cells = []
    for it in items:
        path, _, text = it.partition(':')
        im = Image.open(path).convert('RGB')
        im = im.resize((W, int(im.height * W / im.width)), Image.LANCZOS)
        cells.append((im, text))
    rows = [cells[i:i + 2] for i in range(0, len(cells), 2)]
    th = 90
    H = th + sum(max(c[0].height for c in r) + cap + pad for r in rows) + pad
    board = Image.new('RGB', (2 * W + 3 * pad, H), BG)
    d = ImageDraw.Draw(board)
    ft = ImageFont.truetype(FONT, 52)
    fc = ImageFont.truetype(FONT, 28)
    d.text((board.width // 2, 50), title, font=ft, fill=PINK, anchor='mm')
    y = th
    for r in rows:
        x = pad
        for im, text in r:
            board.paste(im, (x, y))
            d.rounded_rectangle((x - 3, y - 3, x + im.width + 3, y + im.height + 3), 14, outline=(107, 74, 58), width=4)
            d.text((x + 6, y + im.height + 12), text, font=fc, fill=INK)
            x += W + pad
        y += max(c[0].height for c in r) + cap + pad
    board.save(out)
    print('wrote', out, board.size)


main()

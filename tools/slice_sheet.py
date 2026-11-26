# 3×3 などに並べて作ってもらった1枚の画像を、1個ずつに切り分ける。
#
#   python tools/slice_sheet.py sheet.png ore iron cuore copper steel charcoal glass clay brick
#   python tools/slice_sheet.py sheet.png 低木 … --out img/node
#
# 置き場所は種別ごとに分ける。アイテムと採取場所で同じ名前（stone など）が
# あるため、ひとつの入れ物に混ぜると上書きしてしまう。
#   img/item/<名前>.png   物・道具・設備・住民
#   img/node/<名前>.png   採取場所
#   img/area/<名前>.png   エリア
#   img/seed/<名前>.png   種
#
# 名前は左上から右へ、上の段から順に並べる。IMAGE_PROMPTS.md の
# 枠に書いてある順そのまま。
#
# やっていること
#   1. 画像を列数×段数で等分する
#   2. 升目ごとに、背景色（#14110e）でない所を探して切り詰める
#      → 升目の間のすき間や、物の位置のずれを吸収する
#   3. 正方形の背景に中央で置き直し、決めた大きさに縮める
#
# 切り詰めたくないときは --no-trim。背景が別の色のときは --bg '#000000'。

import argparse
import math
import os
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit('Pillow が入っていません。 python -m pip install Pillow')

BG = '#14110e'


def hex2rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def content_box(im, bg, tol):
    """背景でない所を囲む枠。見つからなければ None"""
    px = im.load()
    w, h = im.size
    x0, y0, x1, y1 = w, h, -1, -1
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y][:3]
            if (abs(r - bg[0]) + abs(g - bg[1]) + abs(b - bg[2])) > tol:
                if x < x0:
                    x0 = x
                if y < y0:
                    y0 = y
                if x > x1:
                    x1 = x
                if y > y1:
                    y1 = y
    if x1 < 0:
        return None
    return (x0, y0, x1 + 1, y1 + 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('sheet', help='まとめて作ってもらった1枚の画像')
    ap.add_argument('names', nargs='+', help='左上から読む順の名前')
    ap.add_argument('--cols', type=int, default=3)
    ap.add_argument('--rows', type=int, default=0, help='既定は名前の数から決める')
    ap.add_argument('--out', default='img/item')
    ap.add_argument('--size', type=int, default=256, help='1枚の出来上がりの辺')
    ap.add_argument('--pad', type=float, default=0.10, help='周囲の余白の割合')
    ap.add_argument('--bg', default=BG)
    ap.add_argument('--tol', type=int, default=24, help='背景と見なす色の幅')
    ap.add_argument('--no-trim', action='store_true')
    ap.add_argument('--force', action='store_true', help='あるファイルを上書きする')
    a = ap.parse_args()

    bg = hex2rgb(a.bg)
    rows = a.rows or int(math.ceil(len(a.names) / float(a.cols)))
    if rows * a.cols < len(a.names):
        sys.exit('名前が %d 個あるのに %d×%d にしか入りません'
                 % (len(a.names), a.cols, rows))

    im = Image.open(a.sheet).convert('RGB')
    W, H = im.size
    print('%s %d×%d を %d列×%d段 に分けます（升目 %d×%d）'
          % (os.path.basename(a.sheet), W, H, a.cols, rows,
             W // a.cols, H // rows))

    if not os.path.isdir(a.out):
        os.makedirs(a.out)

    exist = [n for n in a.names if os.path.exists(os.path.join(a.out, n + '.png'))]
    if exist and not a.force:
        sys.exit('もうあるので止めました（--force で上書き）: ' + ' '.join(exist))

    empty = []
    for i, name in enumerate(a.names):
        c, r = i % a.cols, i // a.cols
        cell = im.crop((W * c // a.cols, H * r // rows,
                        W * (c + 1) // a.cols, H * (r + 1) // rows))
        note = ''
        if not a.no_trim:
            box = content_box(cell, bg, a.tol)
            if box is None:
                empty.append(name)
                note = '  ← 背景だけでした'
            else:
                cell = cell.crop(box)

        # 正方形の背景に中央で置き直す
        inner = int(a.size * (1 - a.pad * 2))
        cell.thumbnail((inner, inner), Image.LANCZOS)
        out = Image.new('RGB', (a.size, a.size), bg)
        out.paste(cell, ((a.size - cell.size[0]) // 2,
                         (a.size - cell.size[1]) // 2))
        p = os.path.join(a.out, name + '.png')
        out.save(p)
        print('  %-10s %s%s' % (name, p, note))

    print('%d 枚を %s に書き出しました' % (len(a.names), a.out))
    if empty:
        print('中身が無かった升目: %s' % ' '.join(empty))
        print('列数や段数が合っていないか、画像の並びが違うかもしれません。')


if __name__ == '__main__':
    main()

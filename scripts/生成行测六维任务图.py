"""从模块协议生成定性六维任务图。依赖Pillow；不生成个人能力分。"""
from pathlib import Path
import argparse, math, html
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DIMS = [('K', '知识词义'), ('R', '阅读约束'), ('S', '关系建模'),
        ('M', '方法选择'), ('E', '准确执行'), ('T', '停止控制')]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--font', type=Path, help='含中文字符的字体文件')
    args = parser.parse_args()
    fonts = [args.font, Path('/System/Library/Fonts/Supplemental/Songti.ttc'),
             Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')]
    font = next((p for p in fonts if p and p.exists()), None)
    if not font:
        raise SystemExit('请用 --font 指定中文字体文件。')
    rows = []
    for line in (ROOT / '.agents/skills/xingce-strategy/references/modules.md').read_text().splitlines():
        cols = [c.strip() for c in line.strip('|').split('|')]
        if len(cols) == 5 and cols[-1] and set(cols[-1].split()) <= set('KRSMET'):
            rows.append((cols[0], set(cols[-1].split())))
    assert len(rows) == 11, '模块协议应有十一类训练单元'
    W, H = 1500, 2130
    im = Image.new('RGB', (W, H), '#f5f7f8')
    draw = ImageDraw.Draw(im)
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
           '<title>行测十一类六维任务图</title>',
           '<desc>按模块读题协议标出优先观察的维度，不是个人分数或权重。</desc>',
           f'<rect width="{W}" height="{H}" fill="#f5f7f8"/>']
    def text(x, y, s, size=25, color='#23313d', anchor='mm'):
        f = ImageFont.truetype(str(font), size)
        draw.text((x, y), s, font=f, fill=color, anchor=anchor)
        svg.append(f'<text x="{x}" y="{y}" font-family="Songti SC,Noto Serif CJK SC,serif" font-size="{size}" fill="{color}" text-anchor="middle" dominant-baseline="central">{html.escape(s)}</text>')
    def line(a, b, color, width=2):
        draw.line([a, b], fill=color, width=width)
        svg.append(f'<line x1="{a[0]}" y1="{a[1]}" x2="{b[0]}" y2="{b[1]}" stroke="{color}" stroke-width="{width}"/>')
    def circle(x, y, r, fill, stroke):
        draw.ellipse((x-r, y-r, x+r, y+r), fill=fill, outline=stroke, width=3)
        svg.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="3"/>')
    text(750, 64, '行测十一类 · 六维读题地图', 46)
    text(750, 119, '实心点＝优先观察；空心点＝仍可观察。无权重、无能力分、无高低排名。', 26)
    for i, (name, focus) in enumerate(rows):
        col, row = i % 3, i // 3
        x, y = 25 + col * 500, 170 + row * 475
        draw.rounded_rectangle((x, y, x+450, y+445), radius=20, fill='white', outline='#dce3e7', width=2)
        svg.append(f'<rect x="{x}" y="{y}" width="450" height="445" rx="20" fill="white" stroke="#dce3e7" stroke-width="2"/>')
        paused = name in ('数量关系', '图形推理')
        accent = '#70818b' if paused else '#087c83'
        text(x+225, y+42, name, 33)
        cx, cy = x+225, y+225
        points = [(cx+90*math.cos(-math.pi/2+j*math.pi/3), cy+90*math.sin(-math.pi/2+j*math.pi/3)) for j in range(6)]
        for j, (code, label) in enumerate(DIMS):
            px, py = points[j]
            line((cx, cy), (px, py), '#dce3e7')
            line((px, py), points[(j+1)%6], '#ccd7dc')
            chosen = code in focus
            circle(px, py, 10, accent if chosen else 'white', accent if chosen else '#a4b2bc')
            lx = cx+148*math.cos(-math.pi/2+j*math.pi/3)
            ly = cy+130*math.sin(-math.pi/2+j*math.pi/3)
            text(lx, ly, code+' '+label, 24, accent if chosen else '#52636f')
        text(cx, cy-11, '题型要求', 23)
        text(cx, cy+20, '定性关注', 23)
        text(cx, y+401, '暂缓专项 · 仅保留整卷记录' if paused else '先识别任务，再选择够用的方法', 22, accent)
    x, y = 1025, 1595
    for n, s in enumerate(['怎样使用这张图', '先看题型，再找对应读题动作。', '亮点仅表示本项目的设计关注。', '空心点不等于该维度不重要。', '个人六维表现目前全部未测。', '真实答案、用时与求助记录', '才能支持后续教学调整。']):
        text(x+225, y+48+n*49, s, 28 if n==0 else 23)
    text(750, 2090, '依据：模块读题协议｜设计假设，非官方量表｜数量、图推不据此新增专项', 24)
    out = ROOT/'图示'
    out.mkdir(exist_ok=True)
    im.save(out/'行测十一类六维任务图.png')
    svg.append('</svg>')
    (out/'行测十一类六维任务图.svg').write_text('\n'.join(svg))
    print('已生成十一类、六维定性图（PNG与SVG）。')

if __name__ == '__main__':
    main()

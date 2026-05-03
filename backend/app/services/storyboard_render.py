from __future__ import annotations

import hashlib
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def _wrap(text: str, line_len: int = 52, max_lines: int = 3) -> list[str]:
    words = text.split()
    if not words:
        return []
    lines: list[str] = []
    cur: list[str] = []
    cur_len = 0
    for w in words:
        add = len(w) + (1 if cur else 0)
        if cur_len + add > line_len:
            lines.append(" ".join(cur))
            cur = [w]
            cur_len = len(w)
            if len(lines) >= max_lines:
                break
        else:
            cur.append(w)
            cur_len += add
    if cur and len(lines) < max_lines:
        lines.append(" ".join(cur))
    return lines


def render_placeholder_frame(
    out_path: Path,
    title: str,
    scene_number: int,
    frame_index: int,
    seed: int,
    subtitle: str = "",
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    h = hashlib.sha256(f"{seed}:{scene_number}:{frame_index}:{title}".encode()).hexdigest()
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    r2, g2, b2 = int(h[6:8], 16), int(h[8:10], 16), int(h[10:12], 16)
    w, ht = 1024, 576
    img = Image.new("RGB", (w, ht), (r // 2, g // 2, b // 2))
    draw = ImageDraw.Draw(img)
    for i in range(ht):
        blend = i / ht
        rr = int(r * (1 - blend) + r2 * blend) % 256
        gg = int(g * (1 - blend) + g2 * blend) % 256
        bb = int(b * (1 - blend) + b2 * blend) % 256
        draw.line([(0, i), (w, i)], fill=(rr, gg, bb))
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 36)
        font_small = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 22)
    except OSError:
        font = ImageFont.load_default()
        font_small = font
    draw.text((40, 40), f"Scene {scene_number} · Frame {frame_index + 1}", fill=(255, 255, 255), font=font)
    draw.text((40, 100), title[:80], fill=(240, 240, 240), font=font_small)
    if subtitle:
        y = 140
        for line in _wrap(subtitle, line_len=60, max_lines=3):
            draw.text((40, y), line, fill=(220, 220, 220), font=font_small)
            y += 28
    draw.text((40, ht - 48), "CineGraph AI — storyboard placeholder", fill=(200, 200, 200), font=font_small)
    img.save(out_path, format="PNG")

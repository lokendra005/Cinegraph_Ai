from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator

import imageio
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def _fit_and_zoom(img: Image.Image, width: int, height: int, zoom: float, pan_x: float, pan_y: float) -> np.ndarray:
    src = img.convert("RGB")
    sw, sh = src.size
    target_ratio = width / height
    src_ratio = sw / sh if sh else 1.0

    if src_ratio > target_ratio:
        new_w = int(sh * target_ratio)
        x0 = max(0, (sw - new_w) // 2)
        y0 = 0
        cw, ch = new_w, sh
    else:
        new_h = int(sw / target_ratio) if target_ratio else sh
        x0 = 0
        y0 = max(0, (sh - new_h) // 2)
        cw, ch = sw, new_h
    src = src.crop((x0, y0, x0 + cw, y0 + ch))

    zw = max(1, int(cw / zoom))
    zh = max(1, int(ch / zoom))
    max_dx = max(0, cw - zw)
    max_dy = max(0, ch - zh)
    zx = int(max_dx * max(0.0, min(1.0, pan_x)))
    zy = int(max_dy * max(0.0, min(1.0, pan_y)))
    src = src.crop((zx, zy, zx + zw, zy + zh)).resize((width, height), Image.Resampling.LANCZOS)
    return np.asarray(src, dtype=np.uint8)


def _blend(a: np.ndarray, b: np.ndarray, alpha: float) -> np.ndarray:
    t = max(0.0, min(1.0, alpha))
    return ((1.0 - t) * a.astype(np.float32) + t * b.astype(np.float32)).astype(np.uint8)


def _try_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in (
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "arial.ttf",
    ):
        try:
            return ImageFont.truetype(name, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _wrap_words(text: str, max_chars: int) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    lines: list[str] = []
    for raw in text.split("\n"):
        words = raw.split()
        cur = ""
        for w in words:
            cand = f"{cur} {w}".strip()
            if len(cand) <= max_chars:
                cur = cand
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
    return lines


def _render_slate(
    width: int,
    height: int,
    scene_number: int,
    title: str,
    slugline: str,
) -> Image.Image:
    img = Image.new("RGB", (width, height), (12, 14, 22))
    dr = ImageDraw.Draw(img)
    for y in range(height):
        g = int(12 + (y / max(height, 1)) * 28)
        dr.line([(0, y), (width, y)], fill=(g // 3, g // 4, g // 2))
    font_lg = _try_font(42)
    font_sm = _try_font(26)
    font_xs = _try_font(20)
    label = f"SCENE {scene_number}"
    dr.text((72, 72), label, fill=(200, 210, 230), font=font_xs)
    tlines = _wrap_words(title, 28)[:2]
    y0 = height // 2 - 48
    for i, ln in enumerate(tlines):
        dr.text((72, y0 + i * 48), ln, fill=(245, 248, 255), font=font_lg)
    slines = _wrap_words(slugline, 40)[:3]
    y1 = y0 + len(tlines) * 48 + 36
    for i, ln in enumerate(slines):
        dr.text((72, y1 + i * 32), ln, fill=(170, 185, 210), font=font_sm)
    dr.text((72, height - 72), "CineGraph — scene film (motion + dialogue)", fill=(120, 130, 155), font=font_xs)
    return img


def _burn_in_lower_third(rgb: np.ndarray, lines: list[str], width: int, height: int) -> np.ndarray:
    if not lines:
        return rgb
    im = Image.fromarray(rgb)
    dr = ImageDraw.Draw(im)
    font = _try_font(22)
    pad_x, pad_y = 24, 18
    text = "\n".join(lines[:2])
    bbox = dr.multiline_textbbox((0, 0), text, font=font, spacing=4)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    bx0 = pad_x
    by0 = height - th - pad_y * 3
    bx1 = min(width - pad_x, bx0 + tw + pad_x * 2)
    by1 = height - pad_y
    dr.rounded_rectangle((bx0 - 10, by0 - 10, bx1 + 10, by1 + 10), radius=12, fill=(12, 14, 22))
    dr.multiline_text((bx0, by0), text, fill=(238, 242, 250), font=font, spacing=4)
    return np.asarray(im, dtype=np.uint8)


def _motion_pan(progress: float, variant: int) -> tuple[float, float, float]:
    """Return (zoom, pan_x, pan_y) for Ken Burns; zoom in ~1.0–1.12."""
    p = max(0.0, min(1.0, progress))
    zoom = 1.0 + 0.12 * p
    v = variant % 6
    if v == 0:
        return zoom, p, 0.25 + 0.25 * p
    if v == 1:
        return zoom, 1.0 - p, 0.2 + 0.3 * p
    if v == 2:
        return zoom, 0.5 + 0.4 * (p - 0.5), p
    if v == 3:
        return zoom, p * 0.7, 1.0 - p * 0.6
    if v == 4:
        return zoom, 0.3 + 0.4 * p, 0.35
    return zoom, p * p, 0.5 + 0.2 * p


def _dialogue_cues(script: dict) -> list[str]:
    out: list[str] = []
    for d in script.get("dialogues") or []:
        sp = str(d.get("speaker") or "").strip()
        ln = str(d.get("line") or "").strip()
        if sp and ln:
            out.append(f"{sp}: {ln}")
        elif ln:
            out.append(ln)
    syn = str(script.get("synopsis") or "").strip()
    if not out and syn:
        for chunk in _wrap_words(syn, 52)[:4]:
            out.append(chunk)
    return out


@dataclass
class SceneFilmInput:
    scene_number: int
    title: str
    script: dict
    frame_paths: list[Path]
    motion_seed: int = 0


def iter_scene_film_frames(
    scene: SceneFilmInput,
    width: int = 1280,
    height: int = 720,
    fps: int = 24,
    slate_seconds: float = 2.0,
    seconds_per_beat: float = 1.35,
    crossfade_seconds: float = 0.5,
) -> Iterator[np.ndarray]:
    """Yield RGB uint8 frames for one scene: slate, shot motion, A↔B dissolves, dialogue burn-in."""
    paths = [p for p in scene.frame_paths if p.exists()]
    if not paths:
        raise ValueError("Scene has no frames on disk")

    script = scene.script or {}
    slug = str(script.get("slugline") or "").strip() or f"{scene.title} — live beat"
    slate_img = _render_slate(width, height, scene.scene_number, scene.title, slug)
    slate_frames = max(1, int(slate_seconds * fps))
    for _ in range(slate_frames):
        yield np.asarray(slate_img, dtype=np.uint8)

    images: list[Image.Image] = []
    try:
        for p in paths:
            images.append(Image.open(p).convert("RGB"))
        variant = (scene.motion_seed + scene.scene_number * 17) % 6
        beat_frames = max(8, int(seconds_per_beat * fps))
        xfade_frames = max(6, int(crossfade_seconds * fps)) if len(images) > 1 else 0
        cues = _dialogue_cues(script)
        content_frame_idx = 0
        last_emitted: np.ndarray | None = None

        def cue_for_frame() -> list[str]:
            nonlocal content_frame_idx
            if not cues:
                return []
            slot = content_frame_idx // max(12, fps // 2)
            line = cues[slot % len(cues)]
            return _wrap_words(line, 46)[:2]

        for img_idx, img in enumerate(images):
            for t in range(beat_frames):
                progress = t / max(1, beat_frames - 1)
                zoom, px, py = _motion_pan(progress, variant + img_idx)
                frame = _fit_and_zoom(img, width, height, zoom=zoom, pan_x=px, pan_y=py)
                fc = cue_for_frame()
                if fc:
                    frame = _burn_in_lower_third(frame, fc, width, height)
                last_emitted = frame
                yield frame
                content_frame_idx += 1

            if img_idx < len(images) - 1 and xfade_frames > 0:
                img_b = images[img_idx + 1]
                z_end, px_end, py_end = _motion_pan(1.0, variant + img_idx)
                z_start, px_start, py_start = _motion_pan(0.0, variant + img_idx + 1)
                end_a = _fit_and_zoom(img, width, height, zoom=z_end, pan_x=px_end, pan_y=py_end)
                start_b = _fit_and_zoom(img_b, width, height, zoom=z_start, pan_x=px_start, pan_y=py_start)
                for xf in range(xfade_frames):
                    a = xf / max(1, xfade_frames - 1)
                    frame = _blend(end_a, start_b, a)
                    fc = cue_for_frame()
                    if fc:
                        frame = _burn_in_lower_third(frame, fc, width, height)
                    last_emitted = frame
                    yield frame
                    content_frame_idx += 1

        hold = max(1, int(0.4 * fps))
        if last_emitted is not None:
            for _ in range(hold):
                yield last_emitted
    finally:
        for im in images:
            im.close()


def build_storyboard_video(
    frame_paths: Iterable[Path],
    output_path: Path,
    fps: int = 24,
    seconds_per_frame: float = 1.5,
    width: int = 1280,
    height: int = 720,
) -> int:
    """Legacy: single clip, Ken Burns over each frame in order (slideshow)."""
    paths = [p for p in frame_paths if p.exists()]
    if not paths:
        raise ValueError("No storyboard frames found")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    writer = imageio.get_writer(str(output_path), fps=fps, codec="libx264", quality=8)
    total_written = 0
    frames_per_image = max(1, int(seconds_per_frame * fps))

    try:
        frame: np.ndarray | None = None
        for i, p in enumerate(paths):
            img = Image.open(p)
            for t in range(frames_per_image):
                progress = t / max(1, frames_per_image - 1)
                zoom = 1.0 + 0.1 * progress
                pan_x = progress if i % 2 == 0 else (1.0 - progress)
                pan_y = 0.3 + 0.2 * progress
                frame = _fit_and_zoom(img, width, height, zoom=zoom, pan_x=pan_x, pan_y=pan_y)
                writer.append_data(frame)
                total_written += 1
        if frame is not None:
            for _ in range(int(0.5 * fps)):
                writer.append_data(frame)
                total_written += 1
    finally:
        writer.close()

    return total_written


def build_cinematic_story_video(
    scenes: list[SceneFilmInput],
    output_path: Path,
    fps: int = 24,
    width: int = 1280,
    height: int = 720,
    inter_scene_black_seconds: float = 0.35,
) -> int:
    """Full story: concatenate scene films with short black interstitial."""
    if not scenes:
        raise ValueError("No scenes to render")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    writer = imageio.get_writer(str(output_path), fps=fps, codec="libx264", quality=8)
    total = 0
    black = np.zeros((height, width, 3), dtype=np.uint8)
    gap = max(0, int(inter_scene_black_seconds * fps))
    try:
        for si, sc in enumerate(scenes):
            for frame in iter_scene_film_frames(sc, width=width, height=height, fps=fps):
                writer.append_data(frame)
                total += 1
            if si < len(scenes) - 1 and gap > 0:
                for _ in range(gap):
                    writer.append_data(black)
                    total += 1
    finally:
        writer.close()
    return total


def build_single_scene_film(
    scene: SceneFilmInput,
    output_path: Path,
    fps: int = 24,
    width: int = 1280,
    height: int = 720,
) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    writer = imageio.get_writer(str(output_path), fps=fps, codec="libx264", quality=8)
    total = 0
    try:
        for frame in iter_scene_film_frames(scene, width=width, height=height, fps=fps):
            writer.append_data(frame)
            total += 1
    finally:
        writer.close()
    return total

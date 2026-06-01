"""Gera os ícones/logos do brand do HA a partir das artes Apple.

Especificação HA brands:
- icon: quadrado, 256x256 (icon.png) e 512x512 (icon@2x.png).
- logo: largura até 512 (logo.png) / 1024 (logo@2x.png), altura proporcional.
- variantes dark_*: mesmas dimensões, para temas escuros.

As artes-fonte são pretas sobre fundo branco. Em vez de "tornar branco
transparente" (que deixa franjas), derivamos o alfa da luminância
(alpha = 255 - luminância): preto fica opaco, branco fica transparente, com
anti-aliasing suave. A cor é recolorida para preto (tema claro) ou branco
(tema escuro).

Uso:
    python scripts/make_brand.py <icon_src.png> <logo_src.(png|jpg)> <out_dir> [assets_logo.png]
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image


def _alpha_from_luminance(src: Image.Image) -> Image.Image:
    """Black-on-white art -> RGBA whose alpha is the ink coverage."""
    rgba = src.convert("RGBA")
    white = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
    flat = Image.alpha_composite(white, rgba).convert("L")  # composite over white
    alpha = flat.point(lambda v: 255 - v)  # ink -> opaque, paper -> transparent
    return alpha


def _recolor(alpha: Image.Image, rgb: tuple[int, int, int]) -> Image.Image:
    solid = Image.new("RGBA", alpha.size, (*rgb, 0))
    solid.putalpha(alpha)
    return solid.crop(alpha.getbbox() or (0, 0, *alpha.size))


def _square(img: Image.Image, size: int, pad: float = 0.08) -> Image.Image:
    inner = round(size * (1 - 2 * pad))
    src = img.copy()
    src.thumbnail((inner, inner), Image.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.paste(src, ((size - src.width) // 2, (size - src.height) // 2), src)
    return canvas


def _wide(img: Image.Image, width: int) -> Image.Image:
    ratio = width / img.width
    return img.resize((width, max(1, round(img.height * ratio))), Image.LANCZOS)


def main(icon_src: str, logo_src: str, out_dir: str, assets_logo: str | None) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    icon_alpha = _alpha_from_luminance(Image.open(icon_src))
    logo_alpha = _alpha_from_luminance(Image.open(logo_src))

    icon_light = _recolor(icon_alpha, (0, 0, 0))
    icon_dark = _recolor(icon_alpha, (255, 255, 255))
    logo_light = _recolor(logo_alpha, (0, 0, 0))
    logo_dark = _recolor(logo_alpha, (255, 255, 255))

    _square(icon_light, 256).save(out / "icon.png")
    _square(icon_light, 512).save(out / "icon@2x.png")
    _square(icon_dark, 256).save(out / "dark_icon.png")
    _square(icon_dark, 512).save(out / "dark_icon@2x.png")

    _wide(logo_light, 512).save(out / "logo.png")
    _wide(logo_light, 1024).save(out / "logo@2x.png")
    _wide(logo_dark, 512).save(out / "dark_logo.png")
    _wide(logo_dark, 1024).save(out / "dark_logo@2x.png")

    if assets_logo:
        Path(assets_logo).parent.mkdir(parents=True, exist_ok=True)
        _wide(logo_light, 512).save(assets_logo)

    print(f"Gerado em {out}:")
    for f in sorted(out.glob("*.png")):
        print(" -", f.name, Image.open(f).size)


if __name__ == "__main__":
    if len(sys.argv) not in (4, 5):
        sys.exit(
            "uso: python scripts/make_brand.py <icon_src.png> <logo_src> <out_dir> [assets_logo.png]"
        )
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) == 5 else None)

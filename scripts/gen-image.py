#!/usr/bin/env python3
"""
gen-image.py — Genera la imagen-gancho para WhatsApp (1080x1350).

Enfoque HÍBRIDO:
  1) Nano Banana (Gemini 2.5 Flash Image) genera el FONDO premium on-brand.
  2) Pillow dibuja el TEXTO nítido por encima (titular, chips de rubros, URL),
     para que sea legible sí o sí, sin depender del render de texto de la IA.

Requisitos:
  - Variable de entorno GEMINI_API_KEY (o GOOGLE_API_KEY) con la API key de Nano Banana.
  - pip install pillow requests
Uso:
  GEMINI_API_KEY=xxxx python3 scripts/gen-image.py
Salida:
  ideas/share-banana.png
"""
import os, sys, base64, io, json, urllib.request, pathlib

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
except ImportError:
    sys.exit("Falta Pillow. Instalá con: pip install pillow")
import requests

API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
if not API_KEY:
    sys.exit("Falta GEMINI_API_KEY (o GOOGLE_API_KEY) en el entorno.")

MODEL = "gemini-2.5-flash-image"
W, H = 1080, 1350
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "ideas" / "share-banana.png"

# --- Marca ---
ACC = (124, 58, 237)     # #7c3aed
ACC2 = (168, 85, 247)    # #a855f7
TXT1 = (232, 232, 242)
TXT2 = (152, 152, 176)
TXT3 = (110, 110, 135)

BG_PROMPT = (
    "A premium, modern, dark abstract background for a high-end tech brand. "
    "Deep near-black base with a soft violet (#7c3aed) glow radiating from the top center, "
    "subtle floating 3D geometric panels and soft light streaks suggesting dashboards and automation, "
    "cinematic depth, elegant, minimal, lots of clean negative space in the lower two thirds. "
    "Vertical portrait 4:5 composition. Absolutely NO text, NO letters, NO words, NO logos."
)

def gen_background():
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}"
    body = {
        "contents": [{"parts": [{"text": BG_PROMPT}]}],
        "generationConfig": {"responseModalities": ["IMAGE"]},
    }
    r = requests.post(url, json=body, timeout=120)
    if r.status_code != 200:
        sys.exit(f"Error API Nano Banana ({r.status_code}): {r.text[:500]}")
    data = r.json()
    for cand in data.get("candidates", []):
        for part in cand.get("content", {}).get("parts", []):
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                raw = base64.b64decode(inline["data"])
                return Image.open(io.BytesIO(raw)).convert("RGB")
    sys.exit("La API no devolvió imagen. Respuesta: " + json.dumps(data)[:500])

def cover(img, w, h):
    """Recorta tipo background-size:cover a wxh."""
    iw, ih = img.size
    scale = max(w / iw, h / ih)
    img = img.resize((int(iw * scale), int(ih * scale)), Image.LANCZOS)
    iw, ih = img.size
    return img.crop(((iw - w) // 2, (ih - h) // 2, (iw - w) // 2 + w, (ih - h) // 2 + h))

def font(size, bold=True):
    """Inter si está; si no, Liberation Sans (siempre presente)."""
    candidates = [
        ROOT / "scripts" / ("Inter-Bold.ttf" if bold else "Inter-Regular.ttf"),
        pathlib.Path("/usr/share/fonts/truetype/liberation") / ("LiberationSans-Bold.ttf" if bold else "LiberationSans-Regular.ttf"),
        pathlib.Path("/usr/share/fonts/truetype/dejavu") / ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"),
    ]
    for c in candidates:
        if c.exists():
            return ImageFont.truetype(str(c), size)
    return ImageFont.load_default()

def vgrad(w, h, top_a, bot_a):
    """Gradiente negro vertical (alpha top->bottom)."""
    g = Image.new("L", (1, h))
    for y in range(h):
        t = y / (h - 1)
        g.putpixel((0, y), int(top_a + (bot_a - top_a) * t))
    alpha = g.resize((w, h))
    blk = Image.new("RGBA", (w, h), (0, 0, 0, 255))
    blk.putalpha(alpha)
    return blk

def rounded_pill(draw, xy, radius, fill=None, outline=None, width=1):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)

def main():
    print("→ Generando fondo con Nano Banana…")
    bg = cover(gen_background(), W, H)
    base = bg.convert("RGBA")

    # Oscurecer para legibilidad: leve arriba, fuerte abajo
    base = Image.alpha_composite(base, vgrad(W, H, 40, 230))
    d = ImageDraw.Draw(base)

    M = 72  # margen
    # Marca arriba
    bn = font(34); d.text((M, 70), "Concepto", font=bn, fill=TXT1)
    bw = d.textlength("Concepto ", font=bn)
    d.text((M + bw, 70), "Development", font=bn, fill=ACC2)

    # Eyebrow
    ey = font(26)
    et = "HERRAMIENTA GRATIS"
    etw = d.textlength(et, font=ey)
    rounded_pill(d, (M, 150, M + etw + 56, 200), 25, outline=ACC2, width=2)
    d.ellipse((M + 22, 168, M + 36, 182), fill=ACC2)
    d.text((M + 46, 162), et, font=ey, fill=ACC2)

    # Titular (3 líneas)
    hf = font(86)
    lines = [("Elegí tu rubro.", TXT1), ("Mirá tu negocio en", TXT1), ("piloto automático.", ACC2)]
    y = 260
    for txt, col in lines:
        d.text((M, y), txt, font=hf, fill=col)
        y += 96

    # Subtítulo
    sf = font(32, bold=False)
    d.text((M, y + 14), "Todo negocio tiene tareas que le comen horas.", font=sf, fill=TXT2)
    d.text((M, y + 56), "Mirá cómo se verían en automático.", font=sf, fill=TXT2)

    # Chips de rubros
    chips = ["🏠 Inmobiliaria", "🧱 Barraca", "📊 Estudio", "🛍️ Comercio",
             "🍽️ Gastronomía", "🩺 Salud", "🔧 Servicios", "🏗️ Constructora",
             "💈 Peluquería", "🛒 E-commerce", "✨ y más…"]
    cf = font(28, bold=True)
    cx, cy = M, y + 130
    pad, gap, ch = 22, 14, 56
    for i, c in enumerate(chips):
        cw = d.textlength(c, font=cf) + pad * 2
        if cx + cw > W - M:
            cx = M; cy += ch + gap
        on = (i == 0)
        rounded_pill(d, (cx, cy, cx + cw, cy + ch), 28,
                     fill=ACC if on else (28, 28, 36),
                     outline=None if on else (50, 50, 64), width=2)
        d.text((cx + pad, cy + 12), c, font=cf, fill=(255, 255, 255) if on else TXT2)
        cx += cw + gap

    # URL abajo
    uf = font(48)
    url1, url2 = "conceptodevelopment.com", "/ideas"
    u1w = d.textlength(url1, font=uf)
    total = u1w + d.textlength(url2, font=uf)
    ux = (W - total) // 2
    d.text((ux, H - 150), url1, font=uf, fill=TXT1)
    d.text((ux + u1w, H - 150), url2, font=uf, fill=ACC2)
    ff = font(28, bold=False)
    ft = "Entrá y jugá · es gratis"
    d.text(((W - d.textlength(ft, font=ff)) // 2, H - 90), ft, font=ff, fill=TXT3)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(OUT, "PNG", quality=95)
    print(f"✓ Imagen guardada en {OUT}")

if __name__ == "__main__":
    main()

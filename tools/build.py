#!/usr/bin/env python3.11
"""Build the Camelback Exterior Co. digital card.

    python3.11 tools/build.py https://camelbackexterior.com <google business profile url>

Writes index.html, george.vcf and assets/ (logo, icons, og image, QR) at the repo root.
The card URL is baked into the QR, the vCard and the link-preview tags; the Google Business
Profile URL feeds the "Find Us on Google" button. Re-run when either changes.
"""
import base64
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools" / "_lib"))
import segno  # noqa: E402
from PIL import Image  # noqa: E402

LOGO_SRC = Path.home() / "Apex/01_Projects/PowerWash/brand/camelback_exterior_co_logo.png"
BG = (254, 251, 247)
INK = "#262422"
PHONE = "+16026334042"
EMAIL = "camelbackexteriorco@gmail.com"


def transparent(im):
    """The logo sits on a flat off-white; turn that into alpha so it drops onto any light surface."""
    im = im.convert("RGB")
    out = Image.new("RGBA", im.size)
    src, dst = im.load(), out.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b = src[x, y]
            a = max(1 - r / BG[0], 1 - g / BG[1], 1 - b / BG[2], 0)
            if a < 0.02:
                continue
            un = lambda c, bg: max(0, min(255, round((c - bg * (1 - a)) / a)))
            dst[x, y] = (un(r, BG[0]), un(g, BG[1]), un(b, BG[2]), round(a * 255))
    return out


def fold(line):
    """vCard 3.0 line folding at 75 octets."""
    parts = [line[:75]]
    rest = line[75:]
    while rest:
        parts.append(" " + rest[:74])
        rest = rest[74:]
    return "\r\n".join(parts)


def main():
    if len(sys.argv) != 3 or not all(a.startswith("https://") for a in sys.argv[1:]):
        sys.exit("usage: build.py https://<card url> https://<google business profile url>")
    url, gbp = sys.argv[1].rstrip("/"), sys.argv[2]
    assets = ROOT / "assets"
    assets.mkdir(exist_ok=True)

    full = Image.open(LOGO_SRC).convert("RGB")
    logo = full.crop((74, 330, 1198, 864))
    transparent(logo).save(assets / "logo.webp", quality=92, method=6)

    # square mark: the ridge alone, for the home-screen icon and the contact photo
    ridge = full.crop((150, 350, 1122, 610))
    icon = Image.new("RGB", (1254, 1254), BG)
    icon.paste(ridge, ((1254 - ridge.width) // 2, (1254 - ridge.height) // 2))
    icon.resize((180, 180), Image.LANCZOS).save(assets / "apple-touch-icon.png")
    icon.resize((64, 64), Image.LANCZOS).save(assets / "favicon.png")

    og = Image.new("RGB", (1200, 630), BG)
    w = 900
    lg = logo.resize((w, round(logo.height * w / logo.width)), Image.LANCZOS)
    og.paste(lg, ((1200 - w) // 2, (630 - lg.height) // 2))
    og.save(assets / "og.jpg", quality=90)

    qr = segno.make(url, error="m")
    qr.save(str(assets / "qr.svg"), scale=8, border=1, dark=INK, light=None)
    qr.save(str(assets / "qr.png"), scale=24, border=3, dark=INK, light="#ffffff")

    buf = io.BytesIO()
    full.resize((320, 320), Image.LANCZOS).save(buf, "JPEG", quality=85)
    photo = base64.b64encode(buf.getvalue()).decode()
    vcf = [
        "BEGIN:VCARD",
        "VERSION:3.0",
        "N:Cruz;George;;;",
        "FN:George Cruz",
        "ORG:Camelback Exterior Co.",
        "TITLE:Owner",
        f"TEL;TYPE=CELL,VOICE:{PHONE}",
        f"EMAIL;TYPE=WORK,INTERNET:{EMAIL}",
        f"URL:{url}",
        "ADR;TYPE=WORK:;;;Phoenix;AZ;85016;USA",
        "NOTE:Pressure washing: driveways\\, patios\\, walkways\\, pool decks. Mobile detail: $299 inside and out. "
        "Free quote by text: send a photo of your driveway + your zip.",
        f"PHOTO;ENCODING=b;TYPE=JPEG:{photo}",
        "END:VCARD",
    ]
    (ROOT / "george.vcf").write_bytes(("\r\n".join(fold(l) for l in vcf) + "\r\n").encode())

    html = (ROOT / "tools" / "index.template.html").read_text().replace("{{URL}}", url).replace("{{GBP}}", gbp)
    (ROOT / "index.html").write_text(html)
    (ROOT / ".nojekyll").write_text("")
    print(f"built for {url} · Google button -> {gbp}")
    for p in ["index.html", "george.vcf", *sorted(f"assets/{f.name}" for f in assets.iterdir())]:
        print(f"  {p:28} {(ROOT / p).stat().st_size:>8,} bytes")


if __name__ == "__main__":
    main()

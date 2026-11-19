#!/usr/bin/env python3
"""Static site generator for Holiday House Antica.

Reads:
    content/config.json      phone, e-mail, map, room order, hero image ...
    content/i18n/<lang>.json all texts, one file per language
    photos/<room>/*.jpg      photos, one folder per room (sorted by file name)
    src/templates/*.html     page templates
    src/assets/              css, js, fonts, favicon

Writes the finished website to dist/ – upload that folder to any static host.

Usage:
    python3 build.py            build the site
    python3 build.py --serve    build and preview at http://localhost:8000
"""

import argparse
import base64
import datetime as dt
import functools
import html
import http.server
import json
import os
import re
import shutil
import sys
import urllib.request
from pathlib import Path
from urllib.parse import quote, urlparse

try:
    from PIL import Image, ImageOps
except ImportError:
    sys.exit("Pillow is required for image resizing:  pip install Pillow")

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
CONTENT = ROOT / "content"
PHOTOS = ROOT / "photos"
DIST = ROOT / "dist"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
THUMB_WIDTH = 800
LARGE_WIDTH = 1600
JPEG_QUALITY = 80

# Line icons (24x24, stroke based).
ICON_PATHS = {
    "wifi": '<path d="M5 12.55a11 11 0 0 1 14.08 0"/><path d="M1.42 9a16 16 0 0 1 21.16 0"/><path d="M8.53 16.11a6 6 0 0 1 6.95 0"/><path d="M12 20h.01"/>',
    "tv": '<rect x="2" y="7" width="20" height="15" rx="2"/><path d="m17 2-5 5-5-5"/>',
    "climate": '<path d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0z"/><path d="M19 4v6M16 7h6"/>',
    "kitchen": '<path d="M3 2v7c0 1.1.9 2 2 2h4a2 2 0 0 0 2-2V2"/><path d="M7 2v20"/><path d="M21 15V2a5 5 0 0 0-5 5v6c0 1.1.9 2 2 2h3zm0 0v7"/>',
    "door": '<path d="M13 4h3a2 2 0 0 1 2 2v14"/><path d="M2 20h3"/><path d="M13 20h9"/><path d="M10 12v.01"/><path d="M13 4.56v16.16a1 1 0 0 1-1.24.97L5 20V5.56a2 2 0 0 1 1.51-1.94l4-1A2 2 0 0 1 13 4.56z"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>',
    "waves": '<path d="M2 6c.6.5 1.2 1 2.5 1C7 7 7 5 9.5 5c2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1"/><path d="M2 12c.6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1"/><path d="M2 18c.6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1"/>',
    "parking": '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 17V7h4a3 3 0 0 1 0 6H9"/>',
    "coffee": '<path d="M17 8h1a4 4 0 1 1 0 8h-1"/><path d="M3 8h14v9a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4Z"/><path d="M6 2v2M10 2v2M14 2v2"/>',
    "leaf": '<path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z"/><path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"/>',
    "ship": '<path d="M2 21c.6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1 .6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1"/><path d="M19.38 20A11.6 11.6 0 0 0 21 14l-9-4-9 4c0 2.9.94 5.34 2.81 7.76"/><path d="M19 13V7a2 2 0 0 0-2-2H7a2 2 0 0 0-2 2v6"/><path d="M12 10v4M12 2v3"/>',
    "phone": '<path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/>',
    "mail": '<rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-10 6L2 7"/>',
    "chat": '<path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/>',
    "pin": '<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/>',
    "calendar": '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
    "external": '<path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>',
    "copy": '<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
    "close": '<path d="M18 6 6 18M6 6l12 12"/>',
    "chevron_left": '<path d="m15 18-6-6 6-6"/>',
    "chevron_right": '<path d="m9 18 6-6-6-6"/>',
}


def icon(name: str) -> str:
    return (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" '
        f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICON_PATHS[name]}</svg>'
    )


esc = html.escape


def obfuscate(value: str) -> str:
    """Encode contact data so it never appears as plain text in the HTML.

    main.js reverses this (base64 → UTF-8 → reverse) in the browser, which keeps
    the details readable for visitors but hides them from simple e-mail harvesters.
    """
    return base64.b64encode(value[::-1].encode("utf-8")).decode("ascii")


# --------------------------------------------------------------------------- images

def _resized(im: "Image.Image", max_width: int) -> "Image.Image":
    if im.width <= max_width:
        return im
    height = round(im.height * max_width / im.width)
    return im.resize((max_width, height), Image.LANCZOS)


def process_image(src: Path, out_dir: Path, produced: set) -> dict:
    """Create a thumbnail and a large version of one photo; skip work if up to date."""
    out_dir.mkdir(parents=True, exist_ok=True)
    info = {}
    with Image.open(src) as opened:
        im = ImageOps.exif_transpose(opened).convert("RGB")
        for key, width in (("thumb", THUMB_WIDTH), ("large", LARGE_WIDTH)):
            dest = out_dir / f"{src.stem}-{width}.jpg"
            produced.add(dest)
            version = _resized(im, width)
            if not dest.exists() or dest.stat().st_mtime < src.stat().st_mtime:
                version.save(dest, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
            info[key] = dest.relative_to(DIST).as_posix()
            info[f"{key}_w"], info[f"{key}_h"] = version.size
    return info


def make_og_image(src: Path, produced: set) -> dict:
    """1200×630 crop of the hero photo – the preview shown when the link is shared."""
    dest = DIST / "img" / "og.jpg"
    produced.add(dest)
    if not dest.exists() or dest.stat().st_mtime < src.stat().st_mtime:
        with Image.open(src) as opened:
            im = ImageOps.fit(ImageOps.exif_transpose(opened).convert("RGB"), (1200, 630), Image.LANCZOS)
            im.save(dest, "JPEG", quality=82, optimize=True, progressive=True)
    return {"url": dest.relative_to(DIST).as_posix(), "w": 1200, "h": 630}


def list_photos(folder: Path) -> list:
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.iterdir() if p.suffix.lower() in IMAGE_EXTS)


def srcset(root: str, img: dict) -> str:
    return f"{root}{img['thumb']} {img['thumb_w']}w, {root}{img['large']} {img['large_w']}w"


# --------------------------------------------------------------------------- templating

PLACEHOLDER = re.compile(r"\{\{\s*([\w.\-]+)\s*\}\}")
RAW_PREFIXES = ("html.", "icon.")


def render(template: str, ctx: dict) -> str:
    """Replace {{ dotted.key }} placeholders; values are HTML-escaped unless under html./icon."""

    def lookup(match):
        key = match.group(1)
        value = ctx
        for part in key.split("."):
            if not isinstance(value, dict) or part not in value:
                raise KeyError(f"Unknown template placeholder: {{{{{key}}}}}")
            value = value[part]
        return str(value) if key.startswith(RAW_PREFIXES) else esc(str(value))

    return PLACEHOLDER.sub(lookup, template)


# --------------------------------------------------------------------------- page blocks

def fill(text: str, values: dict) -> str:
    """Replace {name} placeholders in a translated text (unknown names are left as they are)."""
    return re.sub(r"\{(\w+)\}", lambda m: str(values.get(m.group(1), m.group(0))), text)


def number(value, lang: str) -> str:
    """9.5 → '9,5' in languages that use a decimal comma."""
    text = f"{value:g}"
    return text if lang == "en" else text.replace(".", ",")


def block_lang_switcher(langs: list, current: str, root: str, page: str = "") -> str:
    links = []
    for code in langs:
        current_attr = ' aria-current="true"' if code == current else ""
        links.append(
            f'<a href="{root}{code}/{page}" hreflang="{code}" lang="{code}" data-lang="{code}"{current_attr}>{code.upper()}</a>'
        )
    return "".join(links)


def block_hreflang(config: dict, page: str = "") -> str:
    base = config["site_url"]
    tags = [f'<link rel="alternate" hreflang="{c}" href="{base}/{c}/{page}">' for c in config["languages"]]
    if not page:
        tags.append(f'<link rel="alternate" hreflang="x-default" href="{base}/">')
    return "\n  ".join(tags)


def block_reviews(config: dict, t: dict, lang: str) -> str:
    r, tr = config["reviews"], t["reviews"]
    bars = "".join(
        f'<li><span class="rv-cat">{esc(tr["categories"][key])}</span>'
        f'<span class="rv-bar" aria-hidden="true"><span style="width:{score * 10:g}%"></span></span>'
        f'<span class="rv-num">{number(score, lang)}</span></li>'
        for key, score in r["categories"].items()
    )
    quotes = "".join(
        f'<figure class="rv-quote"><blockquote>“{esc(q["text"])}”</blockquote>'
        f'<figcaption>{esc(q["author"])}</figcaption></figure>'
        for q in tr.get("quotes", [])
    )
    return (
        f'<div class="rv-score"><span class="rv-big">{number(r["score"], lang)}</span>'
        f'<span class="rv-word">{esc(tr["score_word"])}</span>'
        f'<span class="rv-based">{esc(fill(tr["based_on"], {"count": r["count"]}))}</span>'
        f'<a class="rv-link" href="{esc(config["booking_url"])}" target="_blank" rel="noopener">'
        f'{esc(tr["read_more"])} {icon("external")}</a></div>'
        f'<ul class="rv-cats">{bars}</ul>'
        + (f'<div class="rv-quotes">{quotes}</div>' if quotes else "")
    )




def block_explore(t: dict) -> str:
    return "".join(
        f'<li class="place reveal"><span class="place-num">{n:02d}</span>'
        f'<div class="place-head"><h3>{esc(item["name"])}</h3><span class="place-dist">{esc(item["distance"])}</span></div>'
        f'<p>{esc(item["text"])}</p></li>'
        for n, item in enumerate(t["explore"]["items"], 1)
    )



def block_fab(config: dict, t: dict, obf: dict) -> str:
    """Floating quick-contact buttons (mainly for phones)."""
    buttons = [
        f'<a class="fab-btn fab-call" href="#contact" data-obf-href="{obf["phone_href"]}" '
        f'aria-label="{esc(t["fab"]["call"])}">{icon("phone")}</a>'
    ]
    if config.get("whatsapp"):
        buttons.insert(0,
            f'<a class="fab-btn fab-wa" href="#contact" data-obf-href="{obfuscate("https://wa.me/" + config["whatsapp"])}" '
            f'target="_blank" rel="noopener" '
            f'aria-label="{esc(t["fab"]["whatsapp"])}">{icon("chat")}</a>'
        )
    return "".join(buttons)


def block_calendar_data(config: dict, t: dict, lang: str, availability: dict) -> str:
    data = {
        "lang": lang,
        "booked": availability["booked"],
        "updated": availability["updated"],
        "seasons": [
            {"periods": s["periods"], "min": s["min_nights"], "price": s["price"]} for s in config["seasons"]
        ],
        "price_pattern": t["prices"]["price_pattern"],
        "t": t["calendar"],
    }
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


# --------------------------------------------------------------------------- availability

def parse_ical(text: str) -> list:
    """Return [from, to) date ranges from the VEVENTs of an iCal feed (Booking, Airbnb ...)."""
    text = re.sub(r"\r?\n[ \t]", "", text)  # unfold continuation lines
    ranges = []
    for event in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", text, flags=re.S):
        start = re.search(r"^DTSTART[^:\n]*:(\d{8})", event, flags=re.M)
        end = re.search(r"^DTEND[^:\n]*:(\d{8})", event, flags=re.M)
        if not start:
            continue
        a = dt.datetime.strptime(start.group(1), "%Y%m%d").date()
        b = dt.datetime.strptime(end.group(1), "%Y%m%d").date() if end else a + dt.timedelta(days=1)
        ranges.append((a, max(b, a + dt.timedelta(days=1))))
    return ranges


def load_availability() -> dict:
    """Booked periods from content/availability.json plus any iCal feeds in $SITE_ICAL_URLS."""
    path = CONTENT / "availability.json"
    manual = load_json(path).get("booked", []) if path.exists() else []
    ranges = [(dt.date.fromisoformat(b["from"]), dt.date.fromisoformat(b["to"])) for b in manual]

    for url in os.environ.get("SITE_ICAL_URLS", "").split():
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (static site build)"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                feed = parse_ical(resp.read().decode("utf-8", "replace"))
            ranges += feed
            print(f"  ✓ calendar feed: {len(feed)} booking(s)")
        except Exception as exc:  # a broken feed must not break the whole site
            print(f"  ! calendar feed could not be loaded ({exc.__class__.__name__}) – skipped")

    # Keep future bookings only and merge overlapping ones.
    today = dt.date.today()
    merged = []
    for a, b in sorted(r for r in ranges if r[1] > today):
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return {
        "booked": [[a.isoformat(), b.isoformat()] for a, b in merged],
        "updated": today.isoformat(),
    }


def block_rooms(rooms: list, t: dict, root: str) -> tuple:
    tabs, panels = [], []
    for i, room in enumerate(rooms):
        name = t["rooms"]["names"].get(room["id"], room["id"])
        active = i == 0
        cover = room["images"][0]
        tabs.append(
            f'<button class="room-tab" type="button" role="tab" id="tab-{room["id"]}" '
            f'aria-controls="panel-{room["id"]}" aria-selected="{str(active).lower()}" tabindex="{0 if active else -1}">'
            f'<img src="{root}{cover["thumb"]}" alt="" width="38" height="38" loading="lazy">'
            f"<span>{esc(name)}</span></button>"
        )
        tiles = []
        for n, img in enumerate(room["images"], 1):
            alt = f"{name} – {n}"
            tiles.append(
                f'<a class="gallery-item" href="{root}{img["large"]}" data-caption="{esc(name)}">'
                f'<img src="{root}{img["thumb"]}" width="{img["thumb_w"]}" height="{img["thumb_h"]}" '
                f'alt="{esc(alt)}" loading="lazy" decoding="async"></a>'
            )
        panels.append(
            f'<div class="room-panel{" is-active" if active else ""}" role="tabpanel" id="panel-{room["id"]}" '
            f'aria-labelledby="tab-{room["id"]}" tabindex="0">'
            f'<div class="room-panel-title"><h3>{esc(name)}</h3></div>'
            f'<div class="gallery" data-count="{len(tiles)}">{"".join(tiles)}</div></div>'
        )
    return "".join(tabs), "\n".join(panels)


def block_contact_cards(config: dict, t: dict) -> str:
    """Contact buttons; phone/e-mail/WhatsApp are obfuscated and filled in by main.js."""
    c = t["contact"]
    subject = quote(c["form"]["subject"])
    # (icon, real href, label, visible value, value is private, opens in new tab)
    cards = [
        ("phone", config["phone_href"], c["call"], config["phone"], True, False),
        ("mail", f'mailto:{config["email"]}?subject={subject}', c["email"], config["email"], True, False),
    ]
    if config.get("whatsapp"):
        cards.append(("chat", f'https://wa.me/{config["whatsapp"]}', c["whatsapp"], c["whatsapp_value"], False, True))
    out = []
    for ic, href, label, value, private_value, external in cards:
        target = ' target="_blank" rel="noopener"' if external else ""
        value_html = (
            f'<span class="cc-value" data-obf-text="{obfuscate(value)}"></span>'
            if private_value
            else f'<span class="cc-value">{esc(value)}</span>'
        )
        out.append(
            f'<a class="contact-card" href="#contact" data-obf-href="{obfuscate(href)}"{target}>'
            f'<span class="cc-icon">{icon(ic)}</span>'
            f'<span><span class="cc-label">{esc(label)}</span>{value_html}</span></a>'
        )
    return "".join(out)


def block_jsonld(config: dict, t: dict, img: dict, lang: str) -> str:
    data = {
        "@context": "https://schema.org",
        "@type": "VacationRental",
        "name": "Holiday House Antica",
        "description": t["meta"]["description"],
        "url": f'{config["site_url"]}/{lang}/',
        "image": f'{config["site_url"]}/{img["hero"]["large"]}',
        # Phone and e-mail are deliberately left out: they would be plain text here.
        "geo": {"@type": "GeoCoordinates", "latitude": config["latitude"], "longitude": config["longitude"]},
        "hasMap": config["map_link_url"],
        "address": {
            "@type": "PostalAddress",
            "addressLocality": config["address_locality"],
            "addressRegion": config["address_region"],
            "addressCountry": config["address_country"],
        },
        "containsPlace": {
            "@type": "Accommodation",
            "occupancy": {"@type": "QuantitativeValue", "maxValue": 6},
            "numberOfBedrooms": 3,
            "numberOfBathroomsTotal": 2,
            "floorSize": {"@type": "QuantitativeValue", "value": 145, "unitCode": "MTK"},
        },
        "checkinTime": config["house_rules"]["checkin_from"],
        "checkoutTime": config["house_rules"]["checkout_until"],
        "petsAllowed": False,
        "amenityFeature": [
            {"@type": "LocationFeatureSpecification", "name": a["text"], "value": True}
            for a in t["amenities"]["items"]
        ],
    }
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


# --------------------------------------------------------------------------- build

def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def warn_placeholders(config: dict) -> None:
    if "example.com" in config["email"] or "000 0000" in config["phone"]:
        print("  ! Placeholder phone/e-mail in use – set SITE_PHONE / SITE_EMAIL before going live.")


# Environment variables override config.json, so real contact details can live in
# CI secrets (e.g. GitHub Actions) instead of the public repository.
ENV_OVERRIDES = {
    "SITE_PHONE": "phone",
    "SITE_EMAIL": "email",
    "SITE_WHATSAPP": "whatsapp",
    "SITE_URL": "site_url",
}


def apply_env_overrides(config: dict) -> None:
    for env_name, key in ENV_OVERRIDES.items():
        value = os.environ.get(env_name, "").strip()
        if value:
            config[key] = value
            print(f"  ✓ {key} taken from ${env_name}")


def build() -> None:
    config = load_json(CONTENT / "config.json")
    apply_env_overrides(config)
    langs = config["languages"]
    translations = {code: load_json(CONTENT / "i18n" / f"{code}.json") for code in langs}

    # Derived config values.
    config["phone_href"] = "tel:" + re.sub(r"[^\d+]", "", config["phone"])
    coords = f'{config["latitude"]},{config["longitude"]}'
    config["map_embed_url"] = f"https://maps.google.com/maps?q={coords}&z=15&output=embed"
    # The Google Maps listing of the house (opens its pin, photos and reviews).
    config["map_link_url"] = config.get("google_maps_url") or f"https://www.google.com/maps/search/?api=1&query={coords}"
    config["year"] = dt.date.today().year
    config["version"] = dt.datetime.now().strftime("%Y%m%d%H%M")
    config["site_url"] = config["site_url"].rstrip("/")

    # Fresh output, but keep already-resized images as a cache.
    DIST.mkdir(exist_ok=True)
    for child in DIST.iterdir():
        if child.name != "img":
            shutil.rmtree(child) if child.is_dir() else child.unlink()
    shutil.copytree(SRC / "assets", DIST / "assets")

    # Photos.
    produced = set()
    rooms = []
    for room_id in config["rooms"]:
        photos = list_photos(PHOTOS / room_id)
        if not photos:
            print(f"  - photos/{room_id}/ is empty – tab hidden")
            continue
        images = [process_image(p, DIST / "img" / room_id, produced) for p in photos]
        rooms.append({"id": room_id, "images": images})
        print(f"  ✓ {room_id}: {len(images)} photo(s)")

    img = {
        "hero": process_image(PHOTOS / config["hero_image"], DIST / "img" / "featured", produced),
        "about": process_image(PHOTOS / config["about_image"], DIST / "img" / "featured", produced),
        "og": make_og_image(PHOTOS / config["hero_image"], produced),
    }
    availability = load_availability()
    print(f"  ✓ calendar: {len(availability['booked'])} booked period(s)")

    # Remove resized images whose source photo was deleted or moved.
    for stale in (DIST / "img").rglob("*.jpg"):
        if stale not in produced:
            stale.unlink()
    for folder in sorted((DIST / "img").glob("*"), reverse=True):
        if folder.is_dir() and not any(folder.iterdir()):
            folder.rmdir()

    # Test mode keeps search engines away until the real contact details are in.
    test_mode = bool(config.get("test_mode"))
    robots_meta = '<meta name="robots" content="noindex, nofollow">' if test_mode else ""

    icons = {name: icon(name) for name in ICON_PATHS}
    page_tpl = (SRC / "templates" / "page.html").read_text(encoding="utf-8")
    root_tpl = (SRC / "templates" / "root.html").read_text(encoding="utf-8")
    privacy_tpl = (SRC / "templates" / "privacy.html").read_text(encoding="utf-8")
    notfound_tpl = (SRC / "templates" / "404.html").read_text(encoding="utf-8")
    hreflang = block_hreflang(config)
    obf = {
        "phone": obfuscate(config["phone"]),
        "phone_href": obfuscate(config["phone_href"]),
        "email": obfuscate(config["email"]),
        "email_href": obfuscate(f'mailto:{config["email"]}'),
        "whatsapp": obfuscate(config.get("whatsapp") or ""),
    }

    for code in langs:
        t = translations[code]
        root = "../"
        room_tabs, room_panels = block_rooms(rooms, t, root)
        blocks = {
            "robots_meta": robots_meta,
            "hreflang": hreflang,
            "lang_switcher": block_lang_switcher(langs, code, root),
            "hero_srcset": srcset(root, img["hero"]),
            "facts": "".join(
                f'<li><span class="fact-value">{esc(f["value"])}</span><span class="fact-label">{esc(f["label"])}</span></li>'
                for f in t["facts"]
            ),
            "about_paragraphs": "".join(f"<p>{esc(p)}</p>" for p in t["about"]["paragraphs"]),
            "room_tabs": room_tabs,
            "room_panels": room_panels,
            "amenities": "".join(
                f'<li class="amenity reveal"><span class="amenity-icon">{icon(a["icon"])}</span><span>{esc(a["text"])}</span></li>'
                for a in t["amenities"]["items"]
            ),
            "location_paragraphs": "".join(f"<p>{esc(p)}</p>" for p in t["location"]["paragraphs"]),
            "distances": "".join(
                f'<li><span class="dist-icon">{icon(d["icon"])}</span>'
                f'<span><span class="dist-value">{esc(d["value"])}</span><span class="dist-label">{esc(d["label"])}</span></span></li>'
                for d in t["location"]["distances"]
            ),
            "contact_cards": block_contact_cards(config, t),
            "jsonld": block_jsonld(config, t, img, code),
            "reviews": block_reviews(config, t, code),
            "price_notes": "".join(f"<li>{esc(n)}</li>" for n in t["prices"]["notes"]),
            "calendar_data": block_calendar_data(config, t, code, availability),
            "explore": block_explore(t),
            "fab": block_fab(config, t, obf),
        }
        ctx = {"lang": code, "root": root, "t": t, "c": config, "img": img, "html": blocks, "icon": icons, "obf": obf}
        out = DIST / code / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render(page_tpl, ctx), encoding="utf-8")
        print(f"  ✓ {code}/index.html")

        # Privacy policy: /<lang>/privacy/
        privacy_root = "../../"
        privacy_blocks = {
            "robots_meta": robots_meta,
            "hreflang": block_hreflang(config, "privacy/"),
            "lang_switcher": block_lang_switcher(langs, code, privacy_root, "privacy/"),
            "sections": "".join(
                f'<h2>{esc(s["h"])}</h2>' + "".join(f"<p>{esc(p)}</p>" for p in s["p"])
                for s in t["privacy"]["sections"]
            ),
        }
        privacy_ctx = dict(ctx, root=privacy_root, html=privacy_blocks)
        out = DIST / code / "privacy" / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render(privacy_tpl, privacy_ctx), encoding="utf-8")

    # Root page: redirects to the visitor's language.
    root_blocks = {
        "robots_meta": robots_meta,
        "hreflang": hreflang,
        "languages_json": json.dumps(langs),
        "lang_gate_links": "".join(
            f'<a href="{c}/" hreflang="{c}" lang="{c}">{esc(translations[c]["lang_name"])}</a>' for c in langs
        ),
    }
    (DIST / "index.html").write_text(
        render(root_tpl, {"c": config, "img": img, "html": root_blocks}), encoding="utf-8"
    )

    # 404 page (GitHub Pages and Cloudflare Pages serve /404.html for unknown URLs).
    # It can be shown at any depth, so it links with absolute paths from the site root.
    base_path = urlparse(config["site_url"]).path.rstrip("/") + "/"
    notfound_blocks = {
        "messages": "".join(
            f'<div class="nf-msg" lang="{c}"><h2>{esc(translations[c]["notfound"]["title"])}</h2>'
            f'<p>{esc(translations[c]["notfound"]["text"])}</p>'
            f'<a class="btn btn-light" href="{base_path}{c}/">{esc(translations[c]["notfound"]["home"])}</a></div>'
            for c in langs
        ),
    }
    (DIST / "404.html").write_text(
        render(notfound_tpl, {"c": config, "img": img, "root": base_path, "html": notfound_blocks}), encoding="utf-8"
    )

    # SEO helpers.
    today = dt.date.today().isoformat()
    urls = "".join(
        f"  <url><loc>{config['site_url']}/{c}/{page}</loc><lastmod>{today}</lastmod></url>\n"
        for c in langs
        for page in ("", "privacy/")
    )
    (DIST / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}</urlset>\n',
        encoding="utf-8",
    )
    robots_txt = (
        "User-agent: *\nDisallow: /\n"
        if test_mode
        else f"User-agent: *\nAllow: /\nSitemap: {config['site_url']}/sitemap.xml\n"
    )
    (DIST / "robots.txt").write_text(robots_txt, encoding="utf-8")

    if test_mode:
        print("  ! test_mode is on – search engines are told not to index the site.")
    warn_placeholders(config)
    print(f"Done → {DIST}")


def serve(port: int) -> None:
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(DIST))
    with http.server.ThreadingHTTPServer(("127.0.0.1", port), handler) as httpd:
        print(f"Preview: http://localhost:{port}/   (Ctrl+C to stop)")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--serve", action="store_true", help="preview the site after building")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    build()
    if args.serve:
        serve(args.port)

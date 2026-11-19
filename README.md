# Holiday House Antica – website

A fully static website (HTML/CSS/JS, no server, no database) in four languages:
Croatian, English, German and Italian. Hosting is free; only the domain costs money.

## Project layout

```
content/
  config.json        phone, e-mail, map, prices, house rules, review score, room order ...
  availability.json  booked periods for the availability calendar (manual)
  i18n/hr.json       all texts – one file per language (hr, en, de, it)
photos/
  bedroom-1/ ...     one folder per room – the site shows exactly these photos
src/
  templates/         page.html (language pages), root.html (language redirect),
                     privacy.html (privacy policy), 404.html (page not found)
  assets/            css, js, fonts, favicon
build.py             generates the finished website into dist/
dist/                OUTPUT – this folder is what gets uploaded
```

## Everyday tasks

**Sort / change photos** – move the files between the folders in `photos/`.
Photos are shown in file-name order and the first one is the room's cover,
so name them `01-...jpg`, `02-...jpg` and so on. Originals can be any size; the build
resizes them. An empty folder simply hides that room.

**Add a new room** – create `photos/<new-id>/`, add `<new-id>` to `rooms` in
`content/config.json`, and add its name under `rooms.names` in all four `i18n/*.json` files.

**Change texts** – edit `content/i18n/<lang>.json`.

**Contact details** – edit `phone`, `email` and `whatsapp` (international number, digits
only, e.g. `385911234567`; set to `""` to hide the button) in `content/config.json`.

**Test mode** – while `"test_mode": true` in `config.json`, every page carries
`noindex` and `robots.txt` blocks crawlers, so Google won't list the test site.
Set it to `false` once the real contact details are in.

**Prices** – `seasons` in `config.json`: periods as `MM-DD` pairs, `price` in EUR per
night for the whole house, `min_nights`. The price is shown under every date in the
availability calendar, and the total is shown when a guest selects dates (with a note if
the stay is shorter than `min_nights`). Dates outside all seasons show no price and cannot be selected.
The notes next to the calendar are `prices.notes` in each `i18n/*.json`.
The current numbers are TEST values.

**Check-in / check-out times** – `house_rules` in `config.json`. They are not shown on
the page, only passed to Google in the page's structured data.

**Reviews** – `reviews` in `config.json` (score, number of reviews, category scores).
To show guest quotes, add them to `reviews.quotes` in each language file:
`{ "text": "Wonderful view ...", "author": "Anna, Germany" }`.

**Availability calendar** – booked periods come from two places:
1. `content/availability.json` – add `{ "from": "2027-07-03", "to": "2027-07-10" }`
   (`to` is the departure day, which counts as free). The two entries there now are TEST data.
2. iCal links in the `SITE_ICAL_URLS` secret (Booking.com: Extranet → Rates & Availability →
   Sync calendars → Export; Airbnb: Calendar → Availability → Export calendar).
   GitHub Actions rebuilds the site every morning, so new bookings appear within a day.
   Note: GitHub pauses scheduled runs in repositories with no commits for 60 days –
   re-enable the workflow under the Actions tab if that happens.

The calendar is a guide for guests; selected dates are copied into the inquiry form.

**Surroundings** – `explore` in each
`i18n/*.json`. Distances are approximate – please check them.

**Map pin** – `latitude` / `longitude` in `config.json` (the embedded map), and
`google_maps_url` – the link behind "Open in Google Maps", pointing to the house's
own Google Maps listing.

## Build and preview

Requires Python 3 and Pillow (`pip install Pillow`).

```bash
python3 build.py            # build into dist/
python3 build.py --serve    # build and open http://localhost:8000
```

## Contact details are kept out of the repository

`build.py` reads these environment variables and they override `config.json`:

| Variable        | Example                       |
|-----------------|-------------------------------|
| `SITE_PHONE`    | `+385 91 123 4567`            |
| `SITE_EMAIL`    | `info@your-domain.com`        |
| `SITE_WHATSAPP` | `385911234567` (digits only)  |
| `SITE_ICAL_URLS`| iCal export links, space-separated |
| `SITE_URL`      | `https://www.your-domain.com` |

`config.json` only holds placeholders. In the generated HTML the phone number and
e-mail are encoded and decoded by JavaScript in the browser, so simple
e-mail harvesters can't read them. Visitors see and click them as usual.

## Publishing (GitHub Pages – free)

Every push to `main` builds and publishes the site via `.github/workflows/deploy.yml`.

1. On GitHub: *Settings → Pages → Build and deployment → Source:* **GitHub Actions**.
2. *Settings → Secrets and variables → Actions*:
   - **Secrets**: `SITE_PHONE`, `SITE_EMAIL`, `SITE_WHATSAPP`
   - **Variables** (optional): `SITE_URL`
3. Push to `main` (or run the workflow manually under *Actions*).
4. Custom domain: *Settings → Pages → Custom domain*, then add the DNS records GitHub shows.

## Alternative: Cloudflare Pages (free)

1. Create a free account at <https://dash.cloudflare.com>.
2. *Workers & Pages → Create → Pages → Upload assets*, name the project, upload the `dist/` folder.
3. *Custom domains → Set up a custom domain* and follow the DNS instructions.
4. Set `site_url` in `config.json` to the final domain, rebuild and upload `dist/` again.

After every change: run `python3 build.py` and upload `dist/` again.
Netlify (drag & drop `dist/` at <https://app.netlify.com/drop>) works the same way.

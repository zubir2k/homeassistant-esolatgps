![esolatgps_banner](/custom_components/esolatgps/brand/logo.png)

![GitHub Repo stars](https://img.shields.io/github/stars/zubir2k/homeassistant-esolatgps?style=social)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/default)
[![hacs_badge](https://img.shields.io/badge/HACS-Integration-41BDF5.svg)](https://github.com/hacs/integration)
![GitHub all releases](https://img.shields.io/badge/dynamic/json?color=41BDF5&logo=home-assistant&label=Download%20Count&suffix=%20installs&cacheSeconds=15600&url=https://analytics.home-assistant.io/custom_integrations.json&query=$.esolatgps.total)
[![Buy](https://img.shields.io/badge/Belanja-Coffee-yellow.svg)](https://zubirco.de/buymecoffee)
![GitHub manifest version (path)](https://img.shields.io/github/manifest-json/v/zubir2k/homeassistant-esolatgps?filename=custom_components%2Fesolatgps%2Fmanifest.json)

Assalamu'alaikum

This is a custom integration for Home Assistant that creates a Prayer Time sensor for each Person based on their GPS coordinates, plus one for your Home zone.

- **In Malaysia:** official JAKIM times via **[waktusolat.app](https://api.waktusolat.app/)**
- **Outside Malaysia:** times from **[Aladhan](https://aladhan.com/prayer-times-api)**, using the nearest local authority (e.g. MUIS in Singapore, Umm Al-Qura in Makkah)

It also ships with the **eSolat GPS Card**, a dashboard card that's installed automatically with the integration.

This is a continuation of [HomeAssistantEsolatGPS](https://github.com/zubir2k/HomeAssistantEsolatGPS) (Appdaemon version)

## What's New
- 🕌 **eSolat GPS Card** bundled with the integration: no dashboard resource to add
- 🌍 Prayer times **outside Malaysia** via Aladhan
- 📍 Sensor state is now the **reverse-geocoded place** (e.g. `Kampung Sungai Jernih, Hulu Langat`)
- 🏷️ New attributes: `flag`, `zone`, `region`, `country`, `provider`, `timezone`
- 🩺 **Diagnostic sensors** per JAKIM zone in use (e.g. `sensor.esolat_sgr01`) and for Aladhan
- 👤 Person sensors are added and removed automatically as GPS comes and goes, with no reload
- ⚡ GPS → JAKIM zone is resolved **offline** from bundled zone maps; JAKIM times are fetched once a month per zone, so even a 5-minute interval barely touches the network
- 🐛 Fixed reverse geolocation for places without a state (e.g. Singapore), which left the sensor unavailable

> [!WARNING]
> **Breaking change:** the sensor state no longer shows the JAKIM zone name (e.g. `Kajang`). If your automations or templates use the old state, switch them to the `zone` attribute.

## Requirements
- Home Assistant 2025.1 or newer
- Person entity with GPS location (device tracker, e.g. the Companion app)

## Installation
#### With HACS
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=zubir2k&repository=homeassistant-esolatgps&category=integration)

> [!Tip]
> If you are unable to use the button above, manually search for eSolat GPS in HACS.

#### Manual
1. Copy the `esolatgps` directory from `custom_components` in this repository and place inside your Home Assistant's `custom_components` directory.
2. Restart Home Assistant
3. Follow the instructions in the `Setup` section

> [!WARNING]
> If installing manually, in order to be alerted about new releases, you will need to subscribe to releases from this repository.

## Setup
[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=esolatgps)

> [!Tip]
> If you are unable to use the button above, follow the steps below:
> 1. Navigate to the Home Assistant Integrations page (Settings --> Devices & Services)
> 2. Click the `+ ADD INTEGRATION` button in the lower right-hand corner
> 3. Search for `eSolat GPS`
> 4. Adjust the interval to your preference. Default is set to 15 minutes.

Setup checks that the JAKIM service (waktusolat.app) can be reached before it finishes. Everything appears under one **eSolat GPS** service in Settings → Devices & Services.

### Options
Both are asked for during setup. Open **Settings → Devices & Services → eSolat GPS → Configure** to change them at any time. The integration reloads on save.

| Option | Default | What it does |
|---|---|---|
| Update interval | 15 min | How often (5 to 60 minutes) each person's location and prayer times are looked up |
| Calculation method outside Malaysia | Auto | The Aladhan method used when someone is outside Malaysia. Auto picks the nearest local authority. JAKIM isn't in the list, because Malaysia always uses JAKIM |

## Sensors

| Entity | Description |
|---|---|
| `sensor.esolat_home` | Prayer times for your Home zone |
| `sensor.esolat_<person>` | Prayer times for each Person with GPS coordinates |
| `sensor.esolatnow` | Current and next prayer for every sensor above, plus today's Hijri date |
| `sensor.esolat_<zone>` | Diagnostic: one per JAKIM zone in use (e.g. `sensor.esolat_sgr01`). State is when its timetable was last fetched; attributes show the state, zone areas, cached month and who is in it |
| `sensor.esolat_aladhan` | Diagnostic: shown while anyone is outside Malaysia. State is the last Aladhan fetch; attributes list the areas, timezones, methods and locations |

> [!NOTE]
> Person sensors follow GPS: a person who gets a tracker gets a sensor on the next update, and one who loses GPS has theirs removed. Zone and Aladhan diagnostics are removed, together with their cached data, once nobody is using them.

### Prayer time sensor

**State:** the reverse-geocoded place, e.g. `Kampung Sungai Jernih, Hulu Langat` or `Bishan, Singapore, SG`.

| Attribute | Example | Notes |
|---|---|---|
| `flag` | `local` / `outside_malaysia` | Where the times come from |
| `zone` | `SGR01` | JAKIM zone code (Malaysia only) |
| `zone_name` | `Gombak, Petaling, Sepang, Hulu Langat, Hulu Selangor, Shah Alam` | JAKIM zone areas (Malaysia only) |
| `hijri` | `1448-05-15` | Hijri date from JAKIM (Malaysia only) |
| `region` | `Selangor` | State or region |
| `country` | `Malaysia` | |
| `provider` | `JAKIM (waktusolat.app)` / `Aladhan` | |
| `method` | `Majlis Ugama Islam Singapura, Singapore` | Calculation authority (outside Malaysia only) |
| `timezone` | `Asia/Kuala_Lumpur` | Local timezone of the location |
| `gps` | `2.99,101.78` | |

Prayer times: `imsak`, `subuh`, `syuruk`, `isyraq`, `dhuha`, `zohor`, `asar`, `maghrib`, `isyak`, each in three formats:
- Datetime UTC (e.g. `2026-10-21T21:49:00+00:00`)
- 12 hours with `_12h` (e.g. `5:49 AM`), in the location's local time
- 24 hours with `_24h` (e.g. `05:49:00`), in the location's local time

## eSolat GPS Card

The card is loaded automatically once the integration is installed. Edit your dashboard, click **Add card**, and search for **eSolat GPS Card**.

<!-- Add a screenshot here, e.g. ![eSolat GPS Card](images/card.png) -->

- Live countdown ring to the next prayer, live clock, Gregorian and Hijri date, moon phase
- Follows the logged-in user's location, and switches to Home times when they're at home
- Full and compact layouts, adapts to phones, tablets and wall displays
- Themes: Sky (changes with the prayer period), Emerald, Midnight, Turquoise, Sable, Slate, or your Home Assistant theme
- Bahasa Melayu or English, 12h or 24h, Zohor shows as Jumaat on Fridays
- Visual editor, no YAML needed

```yaml
type: custom:esolatgps-card
entity: auto              # or sensor.esolat_home / sensor.esolat_<person>
theme: sky                # sky | emerald | midnight | turquoise | sable | slate | ha
language: ms              # ms | en
layout: auto              # auto | full | compact
hour12: true
show_clock: true
show_imsak: true
show_syuruk: true
show_isyraq_dhuha: false
show_moon: true
show_location: true
home_when_home: true      # auto mode: use Home times while the user is home
seconds_threshold: 60     # show MM:SS when the next prayer is this many minutes away
tap_action: more-info     # more-info | none
# title: Waktu Solat
# height: 420px
```

> [!Tip]
> For `entity: auto` to follow each user, link every Person to their Home Assistant user (Settings --> People). Users without a GPS tracker see Home times.

`Sky Theme` changes the background according to the time. More screenshots [here](/screenshots).
![sky-theme](/screenshots/sky-gallery.png)

## How the data updates
- Every update interval, each person's GPS position (and the Home zone) is matched to a JAKIM zone **locally**, using zone maps bundled with the integration. No location is sent anywhere for this step.
- JAKIM's timetable is fetched from waktusolat.app **once per zone per month** and kept in memory. Moving around inside a zone, or two people in the same zone, never triggers a new fetch; entering a new zone fetches that zone once. Timetables are saved in Home Assistant's `.storage`, so a restart or reload reuses them instead of fetching again. A zone nobody is in any more is dropped.
- If a position isn't in any JAKIM zone (outside Malaysia), times come from Aladhan, reused for the rest of the day for the same ~1 km area.
- Place names come from OpenStreetMap (Nominatim), cached for each ~100 m area.
- The Hijri date on `sensor.esolatnow` comes from JAKIM e-Solat once a day.
- `sensor.esolatnow` recalculates the current and next prayer every minute.

## Use cases and examples
- Play the azan at each prayer time where *you* are, not just at home
- Announce Imsak and Maghrib during Ramadhan
- Show the next prayer and a countdown on a wall tablet with the eSolat GPS Card

Automation examples are in [AUTOMATION.md](AUTOMATION.md).

## Known limitations
- Isyraq isn't published by JAKIM. It's calculated as Syuruk + 12 minutes.
- Zone maps are by district. JAKIM's special highland zones (e.g. Genting Highlands, Bukit Larut, Gunung Kinabalu, Gunung Jerai) aren't mapped yet, so those spots get their district's zone.
- JAKIM publishes a year at a time, so the first days of January may be unavailable until the new year's data is released.
- Times outside Malaysia follow Aladhan's calculation, which can differ by a minute or two from the local authority's published timetable.

## Troubleshooting
- **A sensor is unavailable:** check that the person has a GPS location (their tracker shows coordinates), then look at **Settings → System → Logs** for `esolatgps`.
- **Every sensor is unavailable:** waktusolat.app or your internet connection is down. Home Assistant retries automatically, and the log shows it once when it fails and once when it recovers.
- **The place name looks wrong:** it's OpenStreetMap's name for that spot. Prayer times use the JAKIM `zone` attribute, not the place name.
- **Reporting a bug:** open the integration's ⋮ menu → **Download diagnostics** (locations are redacted) and attach it to an [issue](https://github.com/zubir2k/homeassistant-esolatgps/issues).

## Removal
1. Go to **Settings → Devices & Services → eSolat GPS**.
2. Open the ⋮ menu and choose **Delete**. The sensors and the card's dashboard resource are removed.
3. To uninstall the files too, remove eSolat GPS in HACS (or delete `custom_components/esolatgps`) and restart Home Assistant.

## Special Thanks 🎉
- [HomeAssistantMalaysia](https://www.facebook.com/groups/homeassistantmalaysia)
- Saudara [Fareez Iqmal](https://github.com/iqfareez) for his [WaktuSolat API](https://github.com/mptwaktusolat/api-waktusolat-x)
- Prayer times data by [JAKIM](https://www.e-solat.gov.my/) and [Aladhan](https://aladhan.com/)
- JAKIM zone maps from [mptwaktusolat/jakim.geojson](https://github.com/mptwaktusolat/jakim.geojson) (based on [nullifye/malaysia.geojson](https://github.com/nullifye/malaysia.geojson)); rebuild with `scripts/build_zones.py`
- Geolocation data by [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors via Nominatim

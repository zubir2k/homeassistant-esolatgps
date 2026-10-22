![esolatgps_banner](https://user-images.githubusercontent.com/1905339/223016758-1c0c8058-7375-43d9-bd65-9fc00f48809c.png)

![GitHub Repo stars](https://img.shields.io/github/stars/zubir2k/homeassistant-esolatgps?style=social)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/default)
[![hacs_badge](https://img.shields.io/badge/HACS-Integration-41BDF5.svg)](https://github.com/hacs/integration)
![GitHub all releases](https://img.shields.io/badge/dynamic/json?color=41BDF5&logo=home-assistant&label=Download%20Count&suffix=%20installs&cacheSeconds=15600&url=https://analytics.home-assistant.io/custom_integrations.json&query=$.esolatgps.total)
[![Buy](https://img.shields.io/badge/Belanja-Coffee-yellow.svg)](https://zubirco.de/buymecoffee)
![GitHub manifest version (path)](https://img.shields.io/github/manifest-json/v/zubir2k/homeassistant-esolatgps?filename=custom_components%2Fesolatgps%2Fmanifest.json)

Assalamu'alaikum

This is a custom integration for Home Assistant that creates a Prayer Time sensor for each Person based on their GPS coordinates, plus one for your Home zone.

- **In Malaysia:** official JAKIM times via **[Malaysia Prayer Time](https://mpt.i906.my/)**
- **Outside Malaysia:** times from **[Aladhan](https://aladhan.com/prayer-times-api)**, using the nearest local authority (e.g. MUIS in Singapore, Umm Al-Qura in Makkah)

It also ships with the **eSolat GPS Card**, a dashboard card that's installed automatically with the integration.

This is a continuation of [HomeAssistantEsolatGPS](https://github.com/zubir2k/HomeAssistantEsolatGPS) (Appdaemon version)

## What's New
- 🕌 **eSolat GPS Card** bundled with the integration: no dashboard resource to add
- 🌍 Prayer times **outside Malaysia** via Aladhan
- 📍 Sensor state is now the **reverse-geocoded place** (e.g. `Kampung Sungai Jernih, Hulu Langat`)
- 🏷️ New attributes: `flag`, `zone`, `region`, `country`, `provider`, `timezone`
- 🐛 Fixed reverse geolocation for places without a state (e.g. Singapore), which left the sensor unavailable

> [!WARNING]
> **Breaking change:** the sensor state no longer shows the JAKIM zone name (e.g. `Kajang`). If your automations or templates use the old state, switch them to the `zone` attribute.

## Requirements
- Home Assistant 2024.1 or newer (2024.7+ recommended)
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

## Sensors

| Entity | Description |
|---|---|
| `sensor.esolat_home` | Prayer times for your Home zone |
| `sensor.esolat_<person>` | Prayer times for each Person with GPS coordinates |
| `sensor.esolatnow` | Current and next prayer for every sensor above, plus today's Hijri date |

> [!NOTE]
> Person sensors are created when the integration loads. If someone gets a GPS tracker later, reload the integration to create their sensor.

### Prayer time sensor

**State:** the reverse-geocoded place, e.g. `Kampung Sungai Jernih, Hulu Langat` or `Bishan, Singapore, SG`.

| Attribute | Example | Notes |
|---|---|---|
| `flag` | `local` / `outside_malaysia` | Where the times come from |
| `zone` | `Kajang` | JAKIM zone place (Malaysia only) |
| `region` | `Selangor` | State or region |
| `country` | `Malaysia` | |
| `provider` | `JAKIM (MPT)` / `Aladhan` | |
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

## Special Thanks 🎉
- [HomeAssistantMalaysia](https://www.facebook.com/groups/homeassistantmalaysia)
- Saudara [Noorzaini Ilhami](https://github.com/i906) for his [MPT API](https://github.com/MalaysiaPrayerTimes)
- Prayer times data by [JAKIM](https://www.e-solat.gov.my/) and [Aladhan](https://aladhan.com/)
- Geolocation data by [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors via Nominatim

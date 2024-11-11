![esolatgps_banner](https://user-images.githubusercontent.com/1905339/223016758-1c0c8058-7375-43d9-bd65-9fc00f48809c.png)\
[![hacs_badge](https://img.shields.io/badge/HACS-Integration-41BDF5.svg)](https://github.com/hacs/integration)
[![Buy](https://img.shields.io/badge/Belanja-Coffee-yellow.svg)](https://zubirco.de/buymecoffee)
![GitHub manifest version (path)](https://img.shields.io/github/manifest-json/v/zubir2k/homeassistant-esolatgps?filename=custom_components%2Fesolatgps%2Fmanifest.json)

Assalamu'alaikum

This is a custom integration for Home Assistant that will create a Prayer Time sensor based on Person's GPS coordinates.
The GPS-based prayer time API is provided by **[Malaysia Prayer Time](https://mpt.i906.my/)**.

Prayer time information are made as sensor attributes with the following format:
- 12 hours (e.g. 6:01 AM)
- 24 hours (e.g. 06:01:00)
- Datetime UTC (e.g. 2023-07-29T22:01:00+00:00)

This is a continuation of [HomeAssistantEsolatGPS](https://github.com/zubir2k/HomeAssistantEsolatGPS) (Appdaemon version)

## Requirements
- Home Assistant 2021.x and above
- Person entity with GPS location (device tracker)

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

The sensors will be populated `sensor.esolat_` based on the person with GPS coordinates.

![image](https://user-images.githubusercontent.com/1905339/223009818-6e8b483e-a86d-48f7-8f3d-b6fd2035bdae.png)

## Special Thanks 🎉
- [HomeAssistantMalaysia](https://www.facebook.com/groups/homeassistantmalaysia)
- Saudara [Noorzaini Ilhami](https://github.com/i906) for his [MPT API](https://github.com/MalaysiaPrayerTimes)
- Prayer times data by [JAKIM](https://www.e-solat.gov.my/). Geolocation data by [Google](https://www.google.com.my)

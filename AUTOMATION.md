## 🕋 Azan Automation

1. Go to Settings > Automation
2. Create new Automation
3. Edit in YAML
4. Copy-paste below and Save
6. Enable actions in Parallel section according to your preferences

> [!Tip]
> ALEXA: Change the notify action to your own \
> GOOGLE: Change the media_player action to your own

```YAML
alias: 🕋 Azan Automation
description: >-
  Enable actions in the 'Parallel' section according to your preferences. Choose
  to enable either Google or Alexa or both.
triggers:
  - trigger: template
    value_template: >-
      {{ state_attr('sensor.esolatnow','array').home.current in
      ['Subuh','Zohor','Asar','Maghrib','Isyak'] and now().strftime('%H:%M') ==
      as_timestamp(state_attr('sensor.esolatnow','array').home.datetime) |
      timestamp_custom('%H:%M') }}
    alias: Home - 5 Prayers Trigger
    id: esolatnow
conditions: []
actions:
  - variables:
      waktusekarang: "{{ state_attr('sensor.esolatnow','array').home.current }}"
      esolat_tts: >-
        {% set esolatnow = state_attr('sensor.esolatnow','array').home.current
        %} {% if esolatnow == 'Subuh' %}{% set esolat_tts =
        'https://dl.sndup.net/j2nd/tts_subuh.mp3' %} {% elif esolatnow ==
        'Zohor' %}{% set esolat_tts = 'https://dl.sndup.net/bsc9/tts_zohor.mp3'
        %} {% elif esolatnow == 'Asar' %}{% set esolat_tts =
        'https://dl.sndup.net/k5tc/tts_asar.mp3' %} {% elif esolatnow ==
        'Maghrib' %}{% set esolat_tts =
        'https://dl.sndup.net/bfg5/tts_maghrib.mp3' %} {% elif esolatnow ==
        'Isyak' %}{% set esolat_tts = 'https://dl.sndup.net/m822/tts_isyak.mp3'
        %} {% endif %}{{ esolat_tts }}
      esolat_alexa: >-
        {% if esolatnow in ['Zohor','Asar','Maghrib','Isyak'] %}{% set
        esolat_audio = 'https://dl.sndup.net/c62p/azan_alexa.mp3' %} {% elif
        esolatnow == 'Subuh' %}{% set esolat_audio =
        'https://dl.sndup.net/rkrk/azansubuh_alexa.mp3' %} {% endif %}{{
        esolat_audio }}
      esolat_google: >-
        {% if esolatnow in ['Zohor','Asar','Maghrib','Isyak'] %}{% set
        esolat_audio =
        'https://github.com/zubir2k/HomeAssistantAdzan/raw/refs/heads/main/audio/azan_alexa.mp3'
        %} {% elif esolatnow == 'Subuh' %}{% set esolat_audio =
        'https://github.com/zubir2k/HomeAssistantAdzan/raw/refs/heads/main/audio/azansubuh_alexa.mp3'
        %} {% endif %}{{ esolat_audio }}  
    alias: Variables
  - action: persistent_notification.create
    continue_on_error: true
    data:
      message: >-
        {{ now().strftime('%-I:%M %p') }} - Sekarang telah masuk waktu {{
        waktusekarang }} bagi kawasan ini dan kawasan yang sama waktu dengannya.
      notification_id: esolat_azan
      title: 🕋 eSolat - Waktu {{ waktusekarang }}
    alias: HA Notification
  - alias: Parallel - Enable according to your preferences
    parallel:
      - continue_on_error: true
        data:
          data:
            type: tts
          message: <audio src='{{ esolat_tts }}'/><audio src='{{ esolat_alexa }}'/>
        action: notify.alexa_media_zubir_s_echo_pop
        alias: Alexa - Please change the device name
        enabled: false
      - alias: Google - Please change the device name
        sequence:
          - continue_on_error: true
            target:
              entity_id: media_player.all_speaker
            data:
              media_content_id: "{{ esolat_tts }}"
              media_content_type: audio/mp3
              extra:
                title: Azan {{ waktusekarang }}
                thumb: https://i.imgur.com/1U9Ehvr.png
            action: media_player.play_media
            alias: TTS
          - delay:
              hours: 0
              minutes: 0
              seconds: 8
              milliseconds: 0
            alias: Wait for 8 seconds
          - continue_on_error: true
            target:
              entity_id: media_player.all_speaker
            data:
              media_content_id: "{{ esolat_google }}"
              media_content_type: audio/mp3
              extra:
                title: Azan {{ waktusekarang }}
                thumb: https://i.imgur.com/1U9Ehvr.png
            action: media_player.play_media
            alias: Azan
        enabled: false
mode: single
```

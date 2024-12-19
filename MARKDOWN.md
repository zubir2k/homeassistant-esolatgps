## ⌚ Dynamic Prayer Time Card

![image](https://github.com/zubir2k/HomeAssistantEsolatGPS/assets/1905339/3e894bd2-7982-44b9-adbd-024e12a4c3c8)

1. Edit your current dashboard.
2. Add a new Markdown card. ![What is Markdown card?](https://www.home-assistant.io/dashboards/markdown)
3. Copy below markdown.
4. Save

```markdown
> Today is</b><br /><font size=7>{{ now().strftime('%I:%M %p') }}<br />{{ now().strftime('%A') }}</font>
<font size=2>{{ now().strftime('%d %B %Y') }} | {{ state_attr('sensor.esolatnow','hijri') }}</font>
{% set esolat = namespace(array=state_attr('sensor.esolatnow', 'array')) %}
{% for person in states.person | selectattr('name', 'eq', user) %}
{% set userid = person.entity_id | replace('person.', '') | replace(' ', '_') %}
{% set esolat_sensor = 'sensor.esolat_' ~ userid %}
{% if states(esolat_sensor) == 'unknown' or not esolat.array.get(userid) or person.state == 'home' %}
<ha-alert alert-type="info"><b>Waktu Sekarang: </b>{{ esolat.array.get('home').current }} - {{ as_timestamp(esolat.array.get('home').datetime) | timestamp_custom('%I:%M %p') }}<br /><b>Waktu Berikutnya: </b>{{ esolat.array.get('home').next }}</ha-alert>
<table align=center width=100%>
<tr align=center>
<td>Subuh</td>
<td>Zohor</td>
<td>Asar</td>
<td>Maghrib</td>
<td>Isyak</td>
</tr>
<tr align=center>
<td><ha-icon icon="mdi:star-crescent"></ha-icon></td>
<td><ha-icon icon="mdi:star-crescent"></ha-icon></td>
<td><ha-icon icon="mdi:star-crescent"></ha-icon></td>
<td><ha-icon icon="mdi:star-crescent"></ha-icon></td>
<td><ha-icon icon="mdi:star-crescent"></ha-icon></td>
</tr>
<tr align=center>
<td>{{ state_attr('sensor.esolat_home', 'subuh_12h') }}</td>
<td>{{ state_attr('sensor.esolat_home', 'zohor_12h') }}</td>
<td>{{ state_attr('sensor.esolat_home', 'asar_12h') }}</td>
<td>{{ state_attr('sensor.esolat_home', 'maghrib_12h') }}</td>
<td>{{ state_attr('sensor.esolat_home', 'isyak_12h') }}</td>
</tr>
<tr><ha-alert alert-type="info">Location: <b>Home</b> 🏠</ha-alert></tr>
{% else %}
<ha-alert alert-type="info"><b>Waktu Sekarang: </b>{{ esolat.array.get(userid).current }} - {{ as_timestamp(esolat.array.get(userid).datetime) | timestamp_custom('%I:%M %p') }}<br /><b>Waktu Berikutnya: </b>{{ esolat.array.get(userid).next }}</ha-alert>
<table align=center width=100%>
<tr align=center>
<td>Subuh</td>
<td>Zohor</td>
<td>Asar</td>
<td>Maghrib</td>
<td>Isyak</td>
</tr>
<tr align=center>
<td><ha-icon icon="mdi:star-crescent"></ha-icon></td>
<td><ha-icon icon="mdi:star-crescent"></ha-icon></td>
<td><ha-icon icon="mdi:star-crescent"></ha-icon></td>
<td><ha-icon icon="mdi:star-crescent"></ha-icon></td>
<td><ha-icon icon="mdi:star-crescent"></ha-icon></td>
</tr>
<tr align=center>
<td>{{ state_attr(esolat_sensor, 'subuh_12h') }}</td>
<td>{{ state_attr(esolat_sensor, 'zohor_12h') }}</td>
<td>{{ state_attr(esolat_sensor, 'asar_12h') }}</td>
<td>{{ state_attr(esolat_sensor, 'maghrib_12h') }}</td>
<td>{{ state_attr(esolat_sensor, 'isyak_12h') }}</td>
</tr>
<tr><ha-alert alert-type="info"><b>Location: </b>{{ userid }}</ha-alert></tr>
{% endif %}
{% endfor %}
</table>

```

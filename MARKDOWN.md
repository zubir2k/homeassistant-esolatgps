## Dynamic Prayer Time - Markdown Card

1. Edit your current dashboard.
2. Add a new Markdown card.
3. Copy below markdown.
4. Save

```markdown
> Today is</b><br /><font size=7>{{ now().strftime('%I:%M %p') }}<br />{{ now().strftime('%A') }}</font><br /><font size=2>{{ now().strftime('%d %B %Y') }} | {{state_attr('sensor.esolatnow','hijri')}}</font>

{% set esolat = namespace(state_attr('sensor.esolatnow','array')) %}
{% for person in states.person | selectattr('name','eq',user) %}
{% set userid = person.entity_id | replace('person.','') | replace(' ','_') %}
{% if states('sensor.esolat_' ~ userid) == 'unknown' or person.state == 'home' %}
<ha-alert alert-type="info"><b>Waktu Sekarang: </b>{{ esolat[userid].current }} - {{ as_timestamp(esolat[userid].datetime) | timestamp_custom('%I:%M %p') }}<br/><b>Waktu Berikutnya: </b>{{ esolat[userid].next }}</ha-alert>

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
<td>{{ state_attr('sensor.esolat_home','subuh_12h') }}</td>
<td>{{ state_attr('sensor.esolat_home','zohor_12h') }}</td>
<td>{{ state_attr('sensor.esolat_home','asar_12h') }}</td>
<td>{{ state_attr('sensor.esolat_home','maghrib_12h') }}</td>
<td>{{ state_attr('sensor.esolat_home','isyak_12h') }}</td>
<tr><ha-alert alert-type="info">Location: <b>Home</b> 🏠</ha-alert></tr>

{% else %}
<ha-alert alert-type="info"><b>Waktu Sekarang: </b>{{ esolat[userid].current }} - {{ as_timestamp(esolat[userid].datetime) | timestamp_custom('%I:%M %p') }}<br/><b>Waktu Berikutnya: </b>{{ esolat[userid].next }}</ha-alert>

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
<td>{{ state_attr('sensor.esolat_' ~ userid,'subuh_12h') }}</td>
<td>{{ state_attr('sensor.esolat_' ~ userid,'zohor_12h') }}</td>
<td>{{ state_attr('sensor.esolat_' ~ userid,'asar_12h') }}</td>
<td>{{ state_attr('sensor.esolat_' ~ userid,'maghrib_12h') }}</td>
<td>{{ state_attr('sensor.esolat_' ~ userid,'isyak_12h') }}</td>
<tr><ha-alert alert-type="info"><b>Location: </b>{{ states('sensor.esolat_' ~ userid) }}</ha-alert></tr>
{% endif %}
{% endfor %}
</tr>
</table>

```

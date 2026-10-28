"""Config and options flow tests for eSolat GPS."""
from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.esolatgps.const import CONF_ALADHAN_METHOD, DOMAIN

REACH = "custom_components.esolatgps.config_flow._async_can_reach_provider"
SETUP = "custom_components.esolatgps.async_setup_entry"


async def test_user_flow_creates_entry(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with patch(REACH, return_value=True), patch(SETUP, return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_SCAN_INTERVAL: 20, CONF_ALADHAN_METHOD: "11"}
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "eSolat GPS"
    assert result["data"] == {}
    assert result["options"] == {CONF_SCAN_INTERVAL: 20, CONF_ALADHAN_METHOD: "11"}


async def test_setup_form_offers_method_without_jakim(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    schema = {str(k): (k, v) for k, v in result["data_schema"].schema.items()}
    key, selector = schema[CONF_ALADHAN_METHOD]
    assert key.default() == "auto"
    options = selector.config["options"]
    assert "17" not in options
    assert options[0] == "auto"


async def test_user_flow_recovers_from_cannot_connect(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with patch(REACH, return_value=False):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_SCAN_INTERVAL: 15}
        )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}

    with patch(REACH, return_value=True), patch(SETUP, return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_SCAN_INTERVAL: 15}
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_single_instance(hass: HomeAssistant) -> None:
    MockConfigEntry(domain=DOMAIN, data={}).add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_options_flow(hass: HomeAssistant) -> None:
    # An entry made before 0.4.0 keeps the interval in data
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_SCAN_INTERVAL: 30})
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    schema = {str(k): k.default() for k in result["data_schema"].schema}
    assert schema[CONF_SCAN_INTERVAL] == 30
    assert schema[CONF_ALADHAN_METHOD] == "auto"

    with patch(SETUP, return_value=True):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {CONF_SCAN_INTERVAL: 10, CONF_ALADHAN_METHOD: "11"}
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {CONF_SCAN_INTERVAL: 10, CONF_ALADHAN_METHOD: "11"}


async def test_options_flow_drops_legacy_jakim_method(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={CONF_ALADHAN_METHOD: "17"})
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    schema = {str(k): k.default() for k in result["data_schema"].schema}
    assert schema[CONF_ALADHAN_METHOD] == "auto"


async def test_reachability_check(hass: HomeAssistant, mock_http) -> None:
    from custom_components.esolatgps.config_flow import _async_can_reach_provider
    from custom_components.esolatgps.const import WAKTUSOLAT_ZONES_URL
    import aiohttp

    mock_http.get(WAKTUSOLAT_ZONES_URL, json=[])
    assert await _async_can_reach_provider(hass)
    mock_http.clear_requests()
    mock_http.get(WAKTUSOLAT_ZONES_URL, status=503)
    assert not await _async_can_reach_provider(hass)
    mock_http.clear_requests()
    mock_http.get(WAKTUSOLAT_ZONES_URL, exc=aiohttp.ClientError())
    assert not await _async_can_reach_provider(hass)

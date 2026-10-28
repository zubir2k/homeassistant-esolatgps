"""Bundled card registration: Lovelace resource in storage mode, script injection otherwise."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from homeassistant.core import HomeAssistant

from custom_components.esolatgps import card_registration as card

PKG = "custom_components.esolatgps.card_registration"


class FakeResources:
    def __init__(self, items=None, loaded=True):
        self.items = list(items or [])
        self.loaded = loaded
        self.async_create_item = AsyncMock(side_effect=lambda d: self.items.append({"id": "new", **d}))
        self.async_update_item = AsyncMock()
        self.async_delete_item = AsyncMock()

    def async_items(self):
        return self.items

    async def async_get_info(self):
        self.loaded = True


def _lovelace(hass, resources, mode="storage", as_dict=False):
    hass.data["lovelace"] = (
        {"mode": mode, "resources": resources}
        if as_dict
        else SimpleNamespace(resource_mode=mode, resources=resources)
    )


async def _register(hass):
    for key in (card._URL_KEY, card._INJECTED_KEY):
        hass.data.pop(key, None)
    with (
        patch(f"{PKG}._async_register_static_path", AsyncMock()) as static,
        patch(f"{PKG}.add_extra_js_url") as inject,
    ):
        await card.async_register_card(hass)
    return static, inject


async def test_creates_resource_in_storage_mode(hass: HomeAssistant) -> None:
    res = FakeResources(loaded=False)
    _lovelace(hass, res)
    static, inject = await _register(hass)
    static.assert_awaited_once()
    inject.assert_not_called()
    url = res.async_create_item.await_args.args[0]["url"]
    assert url.startswith(f"{card.CARD_URL}?v=0.4.0-")


async def test_updates_old_resource_and_drops_duplicates(hass: HomeAssistant) -> None:
    res = FakeResources(
        [
            {"id": "a", "url": f"{card.CARD_URL}?v=old", "type": "module"},
            {"id": "b", "url": card.CARD_URL, "type": "js"},
            {"id": "c", "url": "/hacsfiles/other.js", "type": "module"},
        ]
    )
    _lovelace(hass, res, as_dict=True)
    await _register(hass)
    assert res.async_update_item.await_args.args[0] == "a"
    res.async_delete_item.assert_awaited_once_with("b")
    res.async_create_item.assert_not_called()


async def test_injects_script_in_yaml_mode(hass: HomeAssistant) -> None:
    _lovelace(hass, FakeResources(), mode="yaml")
    _, inject = await _register(hass)
    inject.assert_called_once()


async def test_injects_when_store_cannot_load(hass: HomeAssistant) -> None:
    res = FakeResources(loaded=False)
    res.async_get_info = AsyncMock(side_effect=RuntimeError)
    _lovelace(hass, res)
    _, inject = await _register(hass)
    inject.assert_called_once()


async def test_injects_when_resource_store_errors(hass: HomeAssistant) -> None:
    res = FakeResources()
    res.async_create_item = AsyncMock(side_effect=ValueError)
    _lovelace(hass, res)
    _, inject = await _register(hass)
    inject.assert_called_once()


async def test_injects_without_lovelace(hass: HomeAssistant) -> None:
    hass.data.pop("lovelace", None)
    _, inject = await _register(hass)
    inject.assert_called_once()


async def test_static_path_and_injection_happen_once(hass: HomeAssistant) -> None:
    _lovelace(hass, FakeResources(), mode="yaml")
    static, inject = await _register(hass)
    with (
        patch(f"{PKG}._async_register_static_path", AsyncMock()) as static2,
        patch(f"{PKG}.add_extra_js_url") as inject2,
    ):
        await card.async_register_card(hass)
    static.assert_awaited_once()
    inject.assert_called_once()
    static2.assert_not_awaited()
    inject2.assert_not_called()


async def test_skips_missing_file(hass: HomeAssistant) -> None:
    _lovelace(hass, FakeResources(), mode="yaml")
    with patch(f"{PKG}.Path.is_file", return_value=False), patch(f"{PKG}.add_extra_js_url") as inject:
        await card.async_register_card(hass)
    inject.assert_not_called()


async def test_resource_restored_after_remove_and_readd(hass: HomeAssistant) -> None:
    """Removing the integration deletes the resource; adding it back must restore it."""
    res = FakeResources()
    _lovelace(hass, res)
    with patch(f"{PKG}._async_register_static_path", AsyncMock()) as static:
        await card.async_register_card(hass)  # HA start
        res.async_delete_item = AsyncMock(
            side_effect=lambda i: res.items.__setitem__(
                slice(None), [x for x in res.items if x["id"] != i]
            )
        )
        await card.async_unregister_card(hass)  # integration removed
        assert res.items == []
        await card.async_register_card(hass)  # integration added back, no restart
    assert len(res.items) == 1
    assert res.items[0]["url"].startswith(f"{card.CARD_URL}?v=")
    static.assert_awaited_once()


async def test_static_path_registration(hass: HomeAssistant) -> None:
    hass.http = SimpleNamespace(async_register_static_paths=AsyncMock())
    await card._async_register_static_path(hass, card.Path("/tmp"))
    cfg = hass.http.async_register_static_paths.await_args.args[0][0]
    assert cfg.url_path == card.CARD_URL_BASE

    hass.http.async_register_static_paths = AsyncMock(side_effect=RuntimeError)
    await card._async_register_static_path(hass, card.Path("/tmp"))  # already registered: no raise


async def test_unregister_removes_only_ours(hass: HomeAssistant) -> None:
    res = FakeResources(
        [{"id": "a", "url": f"{card.CARD_URL}?v=1"}, {"id": "c", "url": "/hacsfiles/other.js"}]
    )
    _lovelace(hass, res)
    await card.async_unregister_card(hass)
    res.async_delete_item.assert_awaited_once_with("a")


async def test_unregister_is_quiet(hass: HomeAssistant) -> None:
    _lovelace(hass, FakeResources(), mode="yaml")
    await card.async_unregister_card(hass)  # nothing to do in YAML mode

    res = FakeResources(loaded=False)
    res.async_get_info = AsyncMock()  # never loads
    _lovelace(hass, res)
    await card.async_unregister_card(hass)
    res.async_delete_item.assert_not_called()

    res = FakeResources([{"id": "a", "url": card.CARD_URL}])
    res.async_delete_item = AsyncMock(side_effect=ValueError)
    _lovelace(hass, res)
    await card.async_unregister_card(hass)  # error is logged, not raised

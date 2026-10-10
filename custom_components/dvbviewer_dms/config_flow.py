from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import DmsApi, DmsApiError
from .const import CONF_VIDEOREC_URL, DEFAULT_PORT, DEFAULT_VIDEOREC_URL, DOMAIN


class DmsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                api = DmsApi(async_get_clientsession(self.hass), f"http://{user_input[CONF_HOST]}:{user_input[CONF_PORT]}", user_input.get(CONF_USERNAME, ""), user_input.get(CONF_PASSWORD, ""))
                await api.async_get_data()
            except DmsApiError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=user_input[CONF_HOST], data=user_input)
        schema = vol.Schema({
            vol.Required(CONF_HOST): str,
            vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.Coerce(int),
            vol.Optional(CONF_USERNAME, default=""): str,
            vol.Optional(CONF_PASSWORD, default=""): str,
            vol.Optional(CONF_VIDEOREC_URL, default=DEFAULT_VIDEOREC_URL): str,
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return DmsOptionsFlowHandler(config_entry)


class DmsOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_VIDEOREC_URL,
                    default=self.config_entry.options.get(
                        CONF_VIDEOREC_URL,
                        self.config_entry.data.get(CONF_VIDEOREC_URL, DEFAULT_VIDEOREC_URL),
                    ),
                ): str,
            }),
        )

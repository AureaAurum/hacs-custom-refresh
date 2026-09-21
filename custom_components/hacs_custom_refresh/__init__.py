"""HACS Custom Refresh integration."""

from __future__ import annotations

import asyncio
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, HACS_DOMAIN, LOGGER, SERVICE_REFRESH


async def async_refresh_custom_repositories(hass: HomeAssistant, lock: asyncio.Lock) -> None:
    """Execute HACS custom repository refresh."""
    LOGGER.info("HACS custom repository refresh started")

    hacs = hass.data.get(HACS_DOMAIN)
    if hacs is None:
        raise HomeAssistantError("HACS integration is not loaded or not installed.")

    system = getattr(hacs, "system", None)
    if system is None or getattr(system, "disabled", False):
        reason = getattr(system, "disabled_reason", "unknown") if system else "system unavailable"
        raise HomeAssistantError(f"HACS is currently disabled (reason: {reason}).")

    stage = getattr(hacs, "stage", None)
    status = getattr(hacs, "status", None)
    is_startup = getattr(status, "startup", True) if status else True

    # In HACS 2.0.5, stage is HacsStage.RUNNING ("running") and status.startup is False when ready
    if stage != "running" or is_startup:
        raise HomeAssistantError(
            f"HACS startup is not completed (stage: {stage}, startup: {is_startup})."
        )

    if not hasattr(hacs, "async_update_downloaded_custom_repositories"):
        raise HomeAssistantError(
            "Required HACS internal API 'async_update_downloaded_custom_repositories' not found."
        )

    if not hasattr(hacs, "async_process_queue"):
        raise HomeAssistantError("Required HACS internal API 'async_process_queue' not found.")

    async with lock:
        try:
            await hacs.async_update_downloaded_custom_repositories()

            # Process queue to execute update tasks immediately and wait for completion
            queue = getattr(hacs, "queue", None)
            if queue is not None:
                timeout_seconds = 120
                start_time = asyncio.get_running_loop().time()
                while getattr(queue, "has_pending_tasks", False) or getattr(
                    queue, "running", False
                ):
                    if getattr(system, "disabled", False):
                        reason = getattr(system, "disabled_reason", "unknown")
                        raise HomeAssistantError(
                            f"HACS was disabled during refresh (reason: {reason})."
                        )

                    if asyncio.get_running_loop().time() - start_time > timeout_seconds:
                        raise HomeAssistantError(
                            "HACS custom repository refresh was queued but did not complete "
                            "within 120 seconds."
                        )

                    if not getattr(queue, "running", False):
                        await hacs.async_process_queue()

                    if getattr(queue, "has_pending_tasks", False) or getattr(
                        queue, "running", False
                    ):
                        await asyncio.sleep(0.5)
            else:
                await hacs.async_process_queue()

            # Brief pause to allow any scheduled events to settle
            await asyncio.sleep(0)

        except HomeAssistantError:
            raise
        except Exception as err:
            LOGGER.exception("Unexpected error during HACS custom repository refresh: %s", err)
            raise HomeAssistantError(f"Failed to refresh HACS custom repositories: {err}") from err

    LOGGER.info("HACS custom repository refresh completed")


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up HACS Custom Refresh component."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HACS Custom Refresh from a config entry."""
    lock = asyncio.Lock()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = lock

    async def handle_refresh(call: ServiceCall) -> None:
        """Handle the refresh service call."""
        await async_refresh_custom_repositories(hass, lock)

    if not hass.services.has_service(DOMAIN, SERVICE_REFRESH):
        hass.services.async_register(DOMAIN, SERVICE_REFRESH, handle_refresh)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if DOMAIN in hass.data:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN, None)
            if hass.services.has_service(DOMAIN, SERVICE_REFRESH):
                hass.services.async_remove(DOMAIN, SERVICE_REFRESH)

    return True

"""Tests for hacs_custom_refresh refresh functionality."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.hacs_custom_refresh import (
    async_refresh_custom_repositories,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.hacs_custom_refresh.const import DOMAIN, HACS_DOMAIN, SERVICE_REFRESH


class MockHacsSystem:
    def __init__(self, disabled: bool = False, disabled_reason: str | None = None):
        self.disabled = disabled
        self.disabled_reason = disabled_reason


class MockHacsStatus:
    def __init__(self, startup: bool = False):
        self.startup = startup


class MockHacsQueue:
    def __init__(self, pending_tasks: int = 0):
        self._pending = pending_tasks
        self.running = False

    @property
    def has_pending_tasks(self) -> bool:
        return self._pending > 0

    def drain(self):
        self._pending = 0


class MockHacs:
    def __init__(
        self,
        stage: str = "running",
        disabled: bool = False,
        disabled_reason: str | None = None,
        startup: bool = False,
        pending_queue_tasks: int = 0,
    ):
        self.stage = stage
        self.system = MockHacsSystem(disabled=disabled, disabled_reason=disabled_reason)
        self.status = MockHacsStatus(startup=startup)
        self.queue = MockHacsQueue(pending_tasks=pending_queue_tasks)
        self.async_update_downloaded_custom_repositories = AsyncMock()
        self.async_process_queue = AsyncMock(side_effect=self._mock_process_queue)
        mock_coordinator = MagicMock()
        mock_coordinator.async_update_listeners = MagicMock()
        self.coordinators = {"integration": mock_coordinator}

    async def _mock_process_queue(self):
        self.queue.drain()


@pytest.fixture
def mock_hass():
    """Fixture for a mock HomeAssistant instance."""
    hass = MagicMock()
    hass.data = {}
    registered_services = {}

    def mock_has_service(domain, service):
        return (domain, service) in registered_services

    def mock_async_register(domain, service, func):
        registered_services[(domain, service)] = func

    def mock_async_remove(domain, service):
        registered_services.pop((domain, service), None)

    hass.services.has_service.side_effect = mock_has_service
    hass.services.async_register.side_effect = mock_async_register
    hass.services.async_remove.side_effect = mock_async_remove
    return hass


@pytest.mark.asyncio
async def test_refresh_success(mock_hass, caplog):
    """Test successful refresh execution."""
    hacs = MockHacs(pending_queue_tasks=2)
    mock_hass.data[HACS_DOMAIN] = hacs
    lock = asyncio.Lock()

    with caplog.at_level("INFO"):
        await async_refresh_custom_repositories(mock_hass, lock)

    hacs.async_update_downloaded_custom_repositories.assert_awaited_once()
    hacs.async_process_queue.assert_awaited_once()
    assert not hacs.queue.has_pending_tasks
    hacs.coordinators["integration"].async_update_listeners.assert_called_once()

    assert "HACS custom repository refresh started" in caplog.text
    assert "HACS custom repository refresh completed" in caplog.text


@pytest.mark.asyncio
async def test_refresh_hacs_not_loaded(mock_hass):
    """Test refresh when HACS is not installed/loaded in hass.data."""
    mock_hass.data = {}
    lock = asyncio.Lock()

    with pytest.raises(HomeAssistantError, match="HACS integration is not loaded or not installed"):
        await async_refresh_custom_repositories(mock_hass, lock)


@pytest.mark.asyncio
async def test_refresh_hacs_disabled(mock_hass):
    """Test refresh when HACS is disabled."""
    hacs = MockHacs(disabled=True, disabled_reason="rate_limit")
    mock_hass.data[HACS_DOMAIN] = hacs
    lock = asyncio.Lock()

    expected_msg = r"HACS is currently disabled \(reason: rate_limit\)"
    with pytest.raises(HomeAssistantError, match=expected_msg):
        await async_refresh_custom_repositories(mock_hass, lock)


@pytest.mark.asyncio
async def test_refresh_hacs_startup_incomplete(mock_hass):
    """Test refresh when HACS is still starting up."""
    hacs = MockHacs(stage="startup", startup=True)
    mock_hass.data[HACS_DOMAIN] = hacs
    lock = asyncio.Lock()

    with pytest.raises(HomeAssistantError, match="HACS startup is not completed"):
        await async_refresh_custom_repositories(mock_hass, lock)


@pytest.mark.asyncio
async def test_refresh_missing_update_api(mock_hass):
    """Test refresh when HACS is missing async_update_downloaded_custom_repositories."""
    hacs = MockHacs()
    del hacs.async_update_downloaded_custom_repositories
    mock_hass.data[HACS_DOMAIN] = hacs
    lock = asyncio.Lock()

    with pytest.raises(
        HomeAssistantError,
        match="Required HACS internal API 'async_update_downloaded_custom_repositories' not found",
    ):
        await async_refresh_custom_repositories(mock_hass, lock)


@pytest.mark.asyncio
async def test_refresh_missing_process_queue_api(mock_hass):
    """Test refresh when HACS is missing async_process_queue."""
    hacs = MockHacs()
    del hacs.async_process_queue
    mock_hass.data[HACS_DOMAIN] = hacs
    lock = asyncio.Lock()

    with pytest.raises(
        HomeAssistantError,
        match="Required HACS internal API 'async_process_queue' not found",
    ):
        await async_refresh_custom_repositories(mock_hass, lock)


@pytest.mark.asyncio
async def test_refresh_concurrency_lock(mock_hass):
    """Test concurrency serialization with lock."""
    hacs = MockHacs()
    mock_hass.data[HACS_DOMAIN] = hacs
    lock = asyncio.Lock()

    call_order = []

    async def slow_update():
        call_order.append("start_slow")
        await asyncio.sleep(0.05)
        call_order.append("end_slow")

    hacs.async_update_downloaded_custom_repositories.side_effect = slow_update

    # Launch two refreshes concurrently
    task1 = asyncio.create_task(async_refresh_custom_repositories(mock_hass, lock))
    task2 = asyncio.create_task(async_refresh_custom_repositories(mock_hass, lock))

    await asyncio.gather(task1, task2)

    assert call_order == ["start_slow", "end_slow", "start_slow", "end_slow"]


@pytest.mark.asyncio
async def test_refresh_queue_already_running_by_hacs(mock_hass):
    """Test behavior when HACS queue is already marked as running."""
    hacs = MockHacs(pending_queue_tasks=2)
    # Simulate HACS background queue processor is currently running
    hacs.queue.running = True
    mock_hass.data[HACS_DOMAIN] = hacs
    lock = asyncio.Lock()

    async def simulate_hacs_background_completion():
        await asyncio.sleep(0.05)
        # HACS finishes running its batch and drains the queue
        hacs.queue.drain()
        hacs.queue.running = False

    asyncio.create_task(simulate_hacs_background_completion())

    await async_refresh_custom_repositories(mock_hass, lock)
    assert not hacs.queue.has_pending_tasks


@pytest.mark.asyncio
async def test_setup_and_unload_entry(mock_hass):
    """Test setup and unload of config entry."""
    entry = MagicMock()
    entry.entry_id = "test_entry_123"

    assert await async_setup_entry(mock_hass, entry)
    assert mock_hass.services.has_service(DOMAIN, SERVICE_REFRESH)
    assert entry.entry_id in mock_hass.data[DOMAIN]

    assert await async_unload_entry(mock_hass, entry)
    assert not mock_hass.services.has_service(DOMAIN, SERVICE_REFRESH)
    assert DOMAIN not in mock_hass.data

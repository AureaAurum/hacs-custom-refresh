"""Tests for hacs_custom_refresh config flow."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from homeassistant import data_entry_flow

from custom_components.hacs_custom_refresh.config_flow import HacsCustomRefreshConfigFlow


@pytest.mark.asyncio
async def test_flow_user_init():
    """Test the initial form is shown."""
    flow = HacsCustomRefreshConfigFlow()
    flow.hass = MagicMock()
    flow._async_current_entries = MagicMock(return_value=[])

    result = await flow.async_step_user()
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"


@pytest.mark.asyncio
async def test_flow_user_creates_entry():
    """Test creating an entry from user input."""
    flow = HacsCustomRefreshConfigFlow()
    flow.hass = MagicMock()
    flow._async_current_entries = MagicMock(return_value=[])

    result = await flow.async_step_user(user_input={})
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "HACS Custom Refresh"
    assert result["data"] == {}


@pytest.mark.asyncio
async def test_flow_single_instance_abort():
    """Test aborting when an entry already exists."""
    flow = HacsCustomRefreshConfigFlow()
    flow.hass = MagicMock()
    flow._async_current_entries = MagicMock(return_value=[MagicMock()])

    result = await flow.async_step_user()
    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"

"""Chrome window maximize via CDP (after FloTorch console login; taskbar stays visible)."""

from __future__ import annotations

import logging

from browser_use.browser import BrowserSession

logger = logging.getLogger(__name__)


async def fullscreen_browser_window(browser_session: BrowserSession) -> bool:
    """Maximize the Chrome window (fills screen; OS taskbar remains visible). Returns True if CDP succeeded."""
    target_id = browser_session.agent_focus_target_id
    if not target_id:
        focused = browser_session.get_focused_target()
        if focused is not None:
            target_id = focused.target_id

    if not target_id:
        logger.warning("fullscreen_browser_window: no focused target")
        return False

    try:
        client = browser_session.cdp_client
        win = await client.send.Browser.getWindowForTarget(params={"targetId": target_id})
        window_id = win.get("windowId")
        if window_id is None:
            logger.warning("fullscreen_browser_window: getWindowForTarget returned no windowId")
            return False

        await client.send.Browser.setWindowBounds(
            params={"windowId": window_id, "bounds": {"windowState": "maximized"}},
        )
        return True
    except Exception as exc:
        logger.warning("fullscreen_browser_window failed: %s", exc)
        return False

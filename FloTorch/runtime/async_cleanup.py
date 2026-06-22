"""Windows-safe asyncio shutdown and browser session teardown."""

from __future__ import annotations

import asyncio
import sys
from typing import Any, Coroutine, TypeVar

T = TypeVar("T")


async def close_browser_session(browser_session: Any) -> None:
    """Fully stop browser-use / Playwright subprocesses before the event loop closes."""
    for method_name in ("kill", "stop"):
        method = getattr(browser_session, method_name, None)
        if not callable(method):
            continue
        try:
            result = method()
            if asyncio.iscoroutine(result):
                await result
        except Exception:
            pass
    # Let Proactor pipe transports drain (avoids "unclosed transport" on Windows).
    await asyncio.sleep(0.5)


async def _drain_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    await asyncio.sleep(0.25)
    pending = [t for t in asyncio.all_tasks(loop) if not t.done()]
    for task in pending:
        task.cancel()
    if pending:
        await asyncio.gather(*pending, return_exceptions=True)
    await loop.shutdown_asyncgens()
    shutdown_executor = getattr(loop, "shutdown_default_executor", None)
    if shutdown_executor is not None:
        await shutdown_executor()


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """Run a coroutine with cleanup suited to browser-use on Windows."""
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        try:
            loop.run_until_complete(_drain_event_loop(loop))
        except Exception:
            pass
        finally:
            asyncio.set_event_loop(None)
            loop.close()

import asyncio
import logging

import uvicorn

from slack_extra.config import config

try:
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass

logging.basicConfig(level="DEBUG" if config.environment != "production" else "INFO")


def start():
    uvicorn.run(
        "slack_extra.utils.starlette:app",
        host="0.0.0.0",
        port=config.port,
        log_level="info" if config.environment != "production" else "warning",
        reload=config.environment == "development",
    )


if __name__ == "__main__":
    start()

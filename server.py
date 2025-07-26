"""
Server script for running the BUPTManus API.
"""

import logging
import uvicorn

# 配置根日志记录器
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    force=True,  # 强制重新配置日志
)

# 设置特定模块的日志级别
logging.getLogger("src").setLevel(logging.INFO)
logging.getLogger("uvicorn").setLevel(logging.INFO)
logging.getLogger("fastapi").setLevel(logging.INFO)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Starting BUPTManus API server")

    # 配置uvicorn的日志
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["default"]["fmt"] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_config["formatters"]["access"]["fmt"] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    uvicorn.run(
        "src.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        log_config=log_config,
    )

import logging
import subprocess
import platform
from typing import Annotated
from langchain_core.tools import tool
from .decorators import log_io

# 初始化日志器
logger = logging.getLogger(__name__)


@tool
@log_io
def bash_tool(
        cmd: Annotated[str, "The bash command to be executed."],
):
    """Use this to execute bash command and do necessary operations."""
    # 1. 自动生成虚拟环境激活命令（跨平台适配）
    system = platform.system()
    activate_cmd = ""

    if system in ["Linux", "Darwin"]:  # Linux/macOS
        # 假设虚拟环境目录为项目根目录下的 .venv
        activate_cmd = "source .venv/bin/activate && "
    elif system == "Windows":  # Windows（PowerShell）
        activate_cmd = ".venv\\Scripts\\Activate.ps1; "
    else:
        logger.warning(f"Unsupported OS: {system}, skip virtualenv activation")
        activate_cmd = ""

    # 2. 拼接激活命令和用户命令
    full_cmd = f"{activate_cmd}{cmd}"
    logger.info(f"Executing Bash Command (with venv activation): {full_cmd}")

    try:
        # 3. 执行命令（捕获 stdout/stderr用于返回结果）
        result = subprocess.run(
            full_cmd,
            shell=True,
            check=True,
            text=True,
            capture_output=True  # 捕获标准输出和错误
        )
        return f"Command executed successfully:\n{result.stdout}"

    except subprocess.CalledProcessError as e:
        error_msg = (
            f"Command failed with exit code {e.returncode}\n"
            f"Error output: {e.stderr}\n"
            f"Command: {full_cmd}"
        )
        logger.error(error_msg)
        return error_msg

    except Exception as e:
        error_msg = f"Unexpected error during command execution: {str(e)}\nCommand: {full_cmd}"
        logger.error(error_msg)
        return error_msg
import subprocess
import sys
import importlib
from typing import Annotated
from langchain_core.tools import tool


@tool
def package_manager_tool(
        action: Annotated[str, "Action to perform: 'install', 'uninstall', or 'check'"],
        package: Annotated[str, "Package name to manage"],
):
    """Manage Python packages in the current environment.

    Actions:
    - install: Install a package using pip
    - uninstall: Uninstall a package
    - check: Check if a package is installed
    """

    if action == "check":
        try:
            importlib.import_module(package)
            return f"Package '{package}' is installed and available"
        except ImportError:
            return f"Package '{package}' is not installed"

    elif action == "install":
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", package],
                capture_output=True, text=True, check=True
            )
            return f"Successfully installed {package}\n{result.stdout}"
        except subprocess.CalledProcessError as e:
            return f"Failed to install {package}\n{e.stderr}"

    elif action == "uninstall":
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "uninstall", "-y", package],
                capture_output=True, text=True, check=True
            )
            return f"Successfully uninstalled {package}\n{result.stdout}"
        except subprocess.CalledProcessError as e:
            return f"Failed to uninstall {package}\n{e.stderr}"

    else:
        return f"Unknown action: {action}. Use 'install', 'uninstall', or 'check'"
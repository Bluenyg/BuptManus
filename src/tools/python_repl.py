import logging
import sys
import os
from pathlib import Path
from typing import Annotated
from langchain_core.tools import tool
from langchain_experimental.utilities import PythonREPL


# Initialize logger
logger = logging.getLogger(__name__)


def get_virtual_env_path():
    """Detect virtual environment path and return site-packages directory."""
    import platform

    # Check if we're in a virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        # We're in a virtual environment
        venv_path = sys.prefix

        # Construct site-packages path based on platform
        if platform.system() == "Windows":
            site_packages = Path(venv_path) / "Lib" / "site-packages"
        else:
            python_version = f"python{sys.version_info.major}.{sys.version_info.minor}"
            site_packages = Path(venv_path) / "lib" / python_version / "site-packages"

        if site_packages.exists():
            return str(site_packages)

    # Fallback: try to find .venv in current or parent directories
    current_dir = Path.cwd()
    for parent in [current_dir] + list(current_dir.parents):
        venv_candidate = parent / ".venv"
        if venv_candidate.exists() and venv_candidate.is_dir():
            # Check for Windows or Unix structure
            if platform.system() == "Windows":
                site_packages = venv_candidate / "Lib" / "site-packages"
            else:
                python_version = f"python{sys.version_info.major}.{sys.version_info.minor}"
                site_packages = venv_candidate / "lib" / python_version / "site-packages"

            if site_packages.exists():
                return str(site_packages)

    return None


def setup_python_path():
    """Ensure virtual environment site-packages is in Python path."""
    venv_site_packages = get_virtual_env_path()

    if venv_site_packages and venv_site_packages not in sys.path:
        # Add to the beginning of sys.path to prioritize venv packages
        sys.path.insert(0, venv_site_packages)
        logger.info(f"Added virtual environment site-packages to Python path: {venv_site_packages}")
        return True

    return False


class EnhancedPythonREPL(PythonREPL):
    """Enhanced PythonREPL that supports uv-installed packages."""

    def __init__(self):
        super().__init__()
        # Setup Python path to include virtual environment packages
        setup_python_path()

    def run(self, command: str, timeout: int | None = None) -> str:
        """Override run method to ensure Python path is properly set."""
        # Get virtual environment path
        venv_site_packages = get_virtual_env_path()

        if venv_site_packages:
            # 创建一个设置脚本，确保虚拟环境包可用
            venv_path_normalized = venv_site_packages.replace('\\', '/')
            setup_code = f"""
import sys
import os

# 添加虚拟环境路径到 sys.path
venv_path = r'{venv_site_packages}'
if venv_path and venv_path not in sys.path:
    sys.path.insert(0, venv_path)

# 设置 PYTHONPATH 环境变量
current_pythonpath = os.environ.get('PYTHONPATH', '')
if venv_path not in current_pythonpath:
    if current_pythonpath:
        os.environ['PYTHONPATH'] = venv_path + os.pathsep + current_pythonpath
    else:
        os.environ['PYTHONPATH'] = venv_path

# 调试信息（可选，在生产环境中可以注释掉）
# print(f"Virtual env site-packages: {{venv_path}}")
# print(f"sys.path contains venv: {{venv_path in sys.path}}")
"""

            # 将设置代码与用户命令组合
            full_command = setup_code + "\n" + command
        else:
            logger.warning("No virtual environment detected, running command without path setup")
            full_command = command

        return super().run(full_command, timeout)


# Initialize enhanced REPL
repl = EnhancedPythonREPL()

# Setup Python path at module level
setup_python_path()


@tool

def python_repl_tool(
        code: Annotated[
            str, "The python code to execute to do further analysis or calculation."
        ],
):
    """Use this to execute python code and do data analysis or calculation. If you want to see the output of a value,
    you should print it out with `print(...)`. This is visible to the user.

    This tool automatically detects and includes packages installed via uv in virtual environments.
    """
    logger.info("Executing Python code")

    # Log current Python path for debugging
    venv_path = get_virtual_env_path()
    if venv_path:
        logger.info(f"Virtual environment site-packages: {venv_path}")
        logger.info(f"Virtual environment in sys.path: {venv_path in sys.path}")

    try:
        # 在执行代码前，添加一个简单的包可用性检查
        if any(pkg in code.lower() for pkg in ['matplotlib', 'numpy', 'pandas', 'scipy']):
            # 如果代码中包含常见的数据科学包，添加导入检查
            check_code = """
# 检查常用包的可用性
import sys
packages_to_check = ['numpy', 'matplotlib', 'pandas', 'scipy']
available_packages = []
for pkg in packages_to_check:
    try:
        __import__(pkg)
        available_packages.append(pkg)
    except ImportError:
        pass

if available_packages:
    print(f"可用的包: {', '.join(available_packages)}")
else:
    print("警告：常用的数据科学包不可用")

print(f"当前Python路径包含 {len(sys.path)} 个目录")
"""
            result = repl.run(check_code + "\n" + code)
        else:
            result = repl.run(code)

        logger.info("Code execution successful")
    except BaseException as e:
        error_msg = f"Failed to execute. Error: {repr(e)}"
        logger.error(error_msg)
        return error_msg

    result_str = f"Successfully executed:\n```python\n{code}\n```\nStdout: {result}"
    return result_str


# Utility function for debugging
def debug_python_env():
    """Debug function to check Python environment and installed packages."""
    venv_path = get_virtual_env_path()

    debug_info = {
        "python_executable": sys.executable,
        "python_path": sys.path,
        "virtual_env_detected": venv_path is not None,
        "virtual_env_path": venv_path,
        "venv_in_path": venv_path in sys.path if venv_path else False
    }

    return debug_info


def check_package_availability(package_name):
    """Check if a package can be imported."""
    try:
        __import__(package_name)
        return True
    except ImportError:
        return False


def list_venv_packages():
    """列出虚拟环境中的所有包"""
    venv_path = get_virtual_env_path()
    if not venv_path:
        return []

    site_packages = Path(venv_path)
    if not site_packages.exists():
        return []

    packages = []
    for item in site_packages.iterdir():
        if item.is_dir() and not item.name.startswith('.') and not item.name.endswith('.dist-info'):
            packages.append(item.name)

    return sorted(packages)


if __name__ == "__main__":
    import platform

    # Test the enhanced REPL
    print("=== System Information ===")
    print(f"Platform: {platform.system()}")
    print(f"Python executable: {sys.executable}")
    print(f"Current directory: {Path.cwd()}")

    print("\n=== Debug Information ===")
    debug_info = debug_python_env()
    for key, value in debug_info.items():
        if key == "python_path":
            print(f"{key}: [showing first 5 paths]")
            for i, path in enumerate(value[:5]):
                print(f"  {i}: {path}")
            if len(value) > 5:
                print(f"  ... and {len(value) - 5} more paths")
        else:
            print(f"{key}: {value}")

    print("\n=== Virtual Environment Packages ===")
    venv_packages = list_venv_packages()
    if venv_packages:
        print(f"Found {len(venv_packages)} packages in virtual environment:")
        for pkg in venv_packages[:20]:  # Show first 20
            print(f"  - {pkg}")
        if len(venv_packages) > 20:
            print(f"  ... and {len(venv_packages) - 20} more packages")
    else:
        print("No packages found in virtual environment")

    print("\n=== Testing Package Availability ===")
    test_packages = ['sys', 'os', 'pathlib', 'matplotlib', 'numpy', 'requests', 'pandas']
    for pkg in test_packages:
        available = check_package_availability(pkg)
        print(f"{pkg}: {'✅ Available' if available else '❌ Not available'}")

    print("\n=== Testing Enhanced Python REPL ===")

    # Test 1: Basic functionality
    print("🔍 Test 1: Basic functionality")
    test_code1 = """
print("Hello from enhanced REPL!")
result = 2 + 2
print(f"2 + 2 = {result}")
"""
    result1 = python_repl_tool(test_code1)
    print("Result:")
    print(result1)
    print("-" * 60)

    # Test 2: Package import test
    print("\n🔍 Test 2: Package import test")
    test_code2 = """
# Test matplotlib import
try:
    import matplotlib
    print(f"✅ matplotlib imported successfully")
    print(f"matplotlib version: {matplotlib.__version__}")
    print(f"matplotlib location: {matplotlib.__file__}")
except ImportError as e:
    print(f"❌ matplotlib import failed: {e}")

# Test numpy import
try:
    import numpy as np
    print(f"✅ numpy imported successfully") 
    print(f"numpy version: {np.__version__}")
    print(f"numpy location: {np.__file__}")
except ImportError as e:
    print(f"❌ numpy import failed: {e}")
"""
    result2 = python_repl_tool(test_code2)
    print("Result:")
    print(result2)

    print("\n🎉 Enhanced Python REPL testing completed!")

    # Final summary
    venv_detected = get_virtual_env_path() is not None
    matplotlib_available = check_package_availability('matplotlib')
    numpy_available = check_package_availability('numpy')

    print(f"\n📋 Summary:")
    print(f"Virtual environment detected: {'✅' if venv_detected else '❌'}")
    print(f"matplotlib available: {'✅' if matplotlib_available else '❌'}")
    print(f"numpy available: {'✅' if numpy_available else '❌'}")

    if venv_detected and (matplotlib_available or numpy_available):
        print("🎉 Everything looks good! REPL should work with your packages.")
    elif venv_detected:
        print("ℹ️  Virtual environment detected but packages not available. Check package installation.")
    else:
        print("⚠️  No virtual environment detected. Packages might not be available.")
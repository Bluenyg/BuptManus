import base64
import time
import requests
import pyautogui
import mss
import os
import subprocess
import platform
from io import BytesIO
from PIL import Image
import webbrowser
import sys
import io
import pyperclip
import unicodedata
import json
import asyncio
import logging
from src.desktop_agent.aiagent import ui_extraction

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

logging.basicConfig(
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)],
    encoding="utf-8",
)

screenshot_requested = False


def type_unicode_smart(text: str, delay: float = 0.05) -> None:
    try:
        text.encode("ascii")

        for idx, line in enumerate(text.split("\n")):
            pyautogui.write(line, interval=delay)
            if idx < len(text.split("\n")) - 1:
                pyautogui.hotkey("shift", "enter")
        return
    except UnicodeEncodeError:
        pass

    old_clip = pyperclip.paste()

    pyperclip.copy(text)
    for _ in range(20):
        if pyperclip.paste() == text:
            break
        time.sleep(0.05)

    hotkey = ("command", "v") if sys.platform == "darwin" else ("ctrl", "v")
    pyautogui.hotkey(*hotkey)
    time.sleep(0.05)

    pyperclip.copy(old_clip)


def windows_direct_app_launch(app_name):
    """修复后的Windows应用启动函数"""
    try:
        # 移除 check=True 参数，因为 Popen 不接受这个参数
        process = subprocess.Popen(f'start "" "{app_name}"', shell=True)
        # 等待一小段时间来检查进程是否成功启动
        time.sleep(1)
        # 检查进程是否还在运行（如果立即退出可能表示失败）
        if process.poll() is None or process.returncode == 0:
            return True
        else:
            print(f"[❌] Process exited with code: {process.returncode}")
            return False
    except Exception as e:
        print(f"[❌] Unexpected error with 'start': {e}")
        return False


def launch_application(app_name):
    """改进的应用启动函数，支持中英文应用名称映射"""
    os_name = platform.system().lower()

    # 中英文应用名称映射
    # 应用名称映射字典
    APP_NAME_MAPPING = {
        # 社交通讯类
        '微信': ['WeChat', 'Weixin', '微信', 'wechat'],
        'weixin': ['WeChat', 'Weixin', '微信', 'wechat'],
        'wechat': ['WeChat', 'Weixin', '微信', 'wechat'],

        'qq': ['QQ', 'qq', 'TencentQQ'],
        'QQ': ['QQ', 'qq', 'TencentQQ'],

        '钉钉': ['DingTalk', 'dingtalk', '钉钉'],
        'dingtalk': ['DingTalk', 'dingtalk', '钉钉'],

        # 音乐播放类
        'qq音乐': ['QQMusic', 'qqmusic', 'QQ音乐', 'Tencent QQMusic'],
        'qqmusic': ['QQMusic', 'qqmusic', 'QQ音乐', 'Tencent QQMusic'],
        'qq音乐应用程序': ['QQMusic', 'qqmusic', 'QQ音乐', 'Tencent QQMusic'],

        '网易云音乐': ['NetEase CloudMusic', 'cloudmusic', '网易云音乐'],
        '网易云': ['NetEase CloudMusic', 'cloudmusic', '网易云音乐'],
        'cloudmusic': ['NetEase CloudMusic', 'cloudmusic', '网易云音乐'],

        '酷狗音乐': ['KuGou', 'kugou', '酷狗音乐'],
        '酷我音乐': ['KuWo', 'kuwo', '酷我音乐'],

        # 浏览器类
        '谷歌浏览器': ['chrome', 'Chrome', 'Google Chrome'],
        '谷歌': ['chrome', 'Chrome', 'Google Chrome'],
        'chrome': ['chrome', 'Chrome', 'Google Chrome'],

        '火狐浏览器': ['firefox', 'Firefox', 'Mozilla Firefox'],
        'firefox': ['firefox', 'Firefox', 'Mozilla Firefox'],

        '微软浏览器': ['msedge', 'Edge', 'Microsoft Edge'],
        'edge': ['msedge', 'Edge', 'Microsoft Edge'],
        'msedge': ['msedge', 'Edge', 'Microsoft Edge'],

        # 办公软件类
        '记事本': ['notepad', 'Notepad'],
        'notepad': ['notepad', 'Notepad'],

        '计算器': ['calc', 'Calculator'],
        'calc': ['calc', 'Calculator'],

        'word': ['WINWORD', 'Microsoft Word', 'Word'],
        'Word': ['WINWORD', 'Microsoft Word', 'Word'],
        '文字处理': ['WINWORD', 'Microsoft Word', 'Word'],

        'excel': ['EXCEL', 'Microsoft Excel', 'Excel'],
        'Excel': ['EXCEL', 'Microsoft Excel', 'Excel'],
        '表格处理': ['EXCEL', 'Microsoft Excel', 'Excel'],

        'powerpoint': ['POWERPNT', 'Microsoft PowerPoint', 'PowerPoint'],
        'PowerPoint': ['POWERPNT', 'Microsoft PowerPoint', 'PowerPoint'],
        '演示文稿': ['POWERPNT', 'Microsoft PowerPoint', 'PowerPoint'],

        # 开发工具类
        'vscode': ['Code', 'Visual Studio Code', 'code'],
        'vs code': ['Code', 'Visual Studio Code', 'code'],
        'visual studio code': ['Code', 'Visual Studio Code', 'code'],

        'pycharm': ['PyCharm', 'pycharm64', 'jetbrains-pycharm'],
        'PyCharm': ['PyCharm', 'pycharm64', 'jetbrains-pycharm'],

        'git bash': ['sh', 'Git Bash', 'bash'],
        'cmd': ['cmd', 'Command Prompt', '命令提示符'],
        '命令提示符': ['cmd', 'Command Prompt', '命令提示符'],

        # 视频播放类
        'vlc': ['vlc', 'VLC media player', 'VLC'],
        'VLC': ['vlc', 'VLC media player', 'VLC'],

        '爱奇艺': ['iQIYI', 'iqiyi', '爱奇艺'],
        'iqiyi': ['iQIYI', 'iqiyi', '爱奇艺'],

        '腾讯视频': ['QQLive', 'qqlivehd', '腾讯视频'],
        'qqlive': ['QQLive', 'qqlivehd', '腾讯视频'],

        # 图像处理类
        'photoshop': ['Photoshop', 'photoshop', 'Adobe Photoshop'],
        'ps': ['Photoshop', 'photoshop', 'Adobe Photoshop'],

        '画图': ['mspaint', 'Paint', '画图'],
        'paint': ['mspaint', 'Paint', '画图'],

        # 系统工具类
        '任务管理器': ['taskmgr', 'Task Manager', '任务管理器'],
        'taskmgr': ['taskmgr', 'Task Manager', '任务管理器'],

        '控制面板': ['control', 'Control Panel', '控制面板'],
        'control': ['control', 'Control Panel', '控制面板'],

        '文件资源管理器': ['explorer', 'File Explorer', '资源管理器'],
        '资源管理器': ['explorer', 'File Explorer', '资源管理器'],
        'explorer': ['explorer', 'File Explorer', '资源管理器'],

        # 下载工具类
        '迅雷': ['Thunder', 'thunder', '迅雷'],
        'thunder': ['Thunder', 'thunder', '迅雷'],

        # 游戏平台类
        'steam': ['Steam', 'steam'],
        'Steam': ['Steam', 'steam'],

        '腾讯游戏': ['WeGame', 'wegame', '腾讯游戏'],
        'wegame': ['WeGame', 'wegame', '腾讯游戏'],
    }

    # 获取可能的应用名称列表
    possible_names = [app_name.lower()]
    for key, names in APP_NAME_MAPPING.items():
        if key in app_name.lower() or app_name.lower() in key:
            possible_names.extend([name.lower() for name in names])

    # 去重并保持顺序
    possible_names = list(dict.fromkeys(possible_names))

    print(f"[INFO] 尝试启动应用: {app_name}, 可能的名称: {possible_names}")

    try:
        if os_name == 'windows':
            # 尝试每个可能的应用名称
            for name in possible_names:
                print(f"[INFO] 尝试启动: {name}")
                if windows_direct_app_launch(name):
                    print(f"[✅] 成功启动: {name}")
                    return

                # 尝试通过PowerShell查找UWP应用
                try:
                    ps_command = f"powershell -Command \"Get-StartApps | Where-Object {{$_.Name -like '*{name}*'}} | Select-Object -First 1 -ExpandProperty AppId\""
                    result = subprocess.run(ps_command, capture_output=True, text=True, shell=True, timeout=10)
                    app_id = result.stdout.strip()
                    if app_id:
                        subprocess.Popen(f'explorer.exe shell:AppsFolder\\{app_id}', shell=True)
                        print(f"[✅] 通过UWP启动: {name}")
                        return
                except subprocess.TimeoutExpired:
                    print(f"[⚠️] PowerShell查询超时: {name}")
                except Exception as e:
                    print(f"[⚠️] PowerShell查询失败: {name}, 错误: {e}")

            print(f"[❌] 所有尝试都失败了: {possible_names}")

        elif os_name == 'darwin':
            for name in possible_names:
                try:
                    subprocess.Popen(["open", "-a", name])
                    print(f"[✅] macOS启动成功: {name}")
                    return
                except:
                    continue

        elif os_name == 'linux':
            for name in possible_names:
                try:
                    subprocess.Popen([name])
                    print(f"[✅] Linux启动成功: {name}")
                    return
                except:
                    continue

    except Exception as e:
        print(f"❌ 启动应用失败 {app_name}: {e}")


def focus_app(app_name):
    """改进的应用聚焦函数，支持中英文应用名称"""
    os_name = platform.system().lower()

    # 使用相同的名称映射逻辑
    # 应用名称映射字典
    APP_NAME_MAPPING = {
        # 社交通讯类
        '微信': ['WeChat', 'Weixin', '微信', 'wechat'],
        'weixin': ['WeChat', 'Weixin', '微信', 'wechat'],
        'wechat': ['WeChat', 'Weixin', '微信', 'wechat'],

        'qq': ['QQ', 'qq', 'TencentQQ'],
        'QQ': ['QQ', 'qq', 'TencentQQ'],

        '钉钉': ['DingTalk', 'dingtalk', '钉钉'],
        'dingtalk': ['DingTalk', 'dingtalk', '钉钉'],

        # 音乐播放类
        'qq音乐': ['QQMusic', 'qqmusic', 'QQ音乐', 'Tencent QQMusic'],
        'qqmusic': ['QQMusic', 'qqmusic', 'QQ音乐', 'Tencent QQMusic'],
        'qq音乐应用程序': ['QQMusic', 'qqmusic', 'QQ音乐', 'Tencent QQMusic'],

        '网易云音乐': ['NetEase CloudMusic', 'cloudmusic', '网易云音乐'],
        '网易云': ['NetEase CloudMusic', 'cloudmusic', '网易云音乐'],
        'cloudmusic': ['NetEase CloudMusic', 'cloudmusic', '网易云音乐'],

        '酷狗音乐': ['KuGou', 'kugou', '酷狗音乐'],
        '酷我音乐': ['KuWo', 'kuwo', '酷我音乐'],

        # 浏览器类
        '谷歌浏览器': ['chrome', 'Chrome', 'Google Chrome'],
        '谷歌': ['chrome', 'Chrome', 'Google Chrome'],
        'chrome': ['chrome', 'Chrome', 'Google Chrome'],

        '火狐浏览器': ['firefox', 'Firefox', 'Mozilla Firefox'],
        'firefox': ['firefox', 'Firefox', 'Mozilla Firefox'],

        '微软浏览器': ['msedge', 'Edge', 'Microsoft Edge'],
        'edge': ['msedge', 'Edge', 'Microsoft Edge'],
        'msedge': ['msedge', 'Edge', 'Microsoft Edge'],

        # 办公软件类
        '记事本': ['notepad', 'Notepad'],
        'notepad': ['notepad', 'Notepad'],

        '计算器': ['calc', 'Calculator'],
        'calc': ['calc', 'Calculator'],

        'word': ['WINWORD', 'Microsoft Word', 'Word'],
        'Word': ['WINWORD', 'Microsoft Word', 'Word'],
        '文字处理': ['WINWORD', 'Microsoft Word', 'Word'],

        'excel': ['EXCEL', 'Microsoft Excel', 'Excel'],
        'Excel': ['EXCEL', 'Microsoft Excel', 'Excel'],
        '表格处理': ['EXCEL', 'Microsoft Excel', 'Excel'],

        'powerpoint': ['POWERPNT', 'Microsoft PowerPoint', 'PowerPoint'],
        'PowerPoint': ['POWERPNT', 'Microsoft PowerPoint', 'PowerPoint'],
        '演示文稿': ['POWERPNT', 'Microsoft PowerPoint', 'PowerPoint'],

        # 开发工具类
        'vscode': ['Code', 'Visual Studio Code', 'code'],
        'vs code': ['Code', 'Visual Studio Code', 'code'],
        'visual studio code': ['Code', 'Visual Studio Code', 'code'],

        'pycharm': ['PyCharm', 'pycharm64', 'jetbrains-pycharm'],
        'PyCharm': ['PyCharm', 'pycharm64', 'jetbrains-pycharm'],

        'git bash': ['sh', 'Git Bash', 'bash'],
        'cmd': ['cmd', 'Command Prompt', '命令提示符'],
        '命令提示符': ['cmd', 'Command Prompt', '命令提示符'],

        # 视频播放类
        'vlc': ['vlc', 'VLC media player', 'VLC'],
        'VLC': ['vlc', 'VLC media player', 'VLC'],

        '爱奇艺': ['iQIYI', 'iqiyi', '爱奇艺'],
        'iqiyi': ['iQIYI', 'iqiyi', '爱奇艺'],

        '腾讯视频': ['QQLive', 'qqlivehd', '腾讯视频'],
        'qqlive': ['QQLive', 'qqlivehd', '腾讯视频'],

        # 图像处理类
        'photoshop': ['Photoshop', 'photoshop', 'Adobe Photoshop'],
        'ps': ['Photoshop', 'photoshop', 'Adobe Photoshop'],

        '画图': ['mspaint', 'Paint', '画图'],
        'paint': ['mspaint', 'Paint', '画图'],

        # 系统工具类
        '任务管理器': ['taskmgr', 'Task Manager', '任务管理器'],
        'taskmgr': ['taskmgr', 'Task Manager', '任务管理器'],

        '控制面板': ['control', 'Control Panel', '控制面板'],
        'control': ['control', 'Control Panel', '控制面板'],

        '文件资源管理器': ['explorer', 'File Explorer', '资源管理器'],
        '资源管理器': ['explorer', 'File Explorer', '资源管理器'],
        'explorer': ['explorer', 'File Explorer', '资源管理器'],

        # 下载工具类
        '迅雷': ['Thunder', 'thunder', '迅雷'],
        'thunder': ['Thunder', 'thunder', '迅雷'],

        # 游戏平台类
        'steam': ['Steam', 'steam'],
        'Steam': ['Steam', 'steam'],

        '腾讯游戏': ['WeGame', 'wegame', '腾讯游戏'],
        'wegame': ['WeGame', 'wegame', '腾讯游戏'],
    }

    possible_names = [app_name.lower()]
    for key, names in APP_NAME_MAPPING.items():
        if key in app_name.lower() or app_name.lower() in key:
            possible_names.extend([name.lower() for name in names])

    possible_names = list(dict.fromkeys(possible_names))
    print(f"[INFO] 尝试聚焦应用: {app_name}, 可能的名称: {possible_names}")

    if os_name == "windows":
        try:
            import win32gui
            import win32con
            import win32api

            def enum_handler(hwnd, match_hwnds):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    # 检查标题是否包含任何可能的应用名称
                    for name in possible_names:
                        if name.lower() in title.lower():
                            match_hwnds.append((hwnd, title))
                            break

            match_hwnds = []
            win32gui.EnumWindows(lambda hwnd, _: enum_handler(hwnd, match_hwnds), None)

            print(f"[INFO] 找到匹配的窗口: {[(title) for _, title in match_hwnds]}")

            for hwnd, title in match_hwnds:
                try:
                    # Check if already in foreground
                    if hwnd == win32gui.GetForegroundWindow():
                        print(f"[INFO] 窗口已经在前台: {title}")
                        return True  # Already focused, don't touch

                    # Only restore if minimized
                    if win32gui.IsIconic(hwnd):
                        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

                    # Simulate ALT key to bypass foreground lock
                    win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)  # Alt down
                    win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)  # Alt up
                    time.sleep(0.05)

                    win32gui.SetForegroundWindow(hwnd)
                    time.sleep(0.1)

                    if hwnd == win32gui.GetForegroundWindow():
                        print(f"[✅] 成功聚焦窗口: {title}")
                        return True
                except Exception as e:
                    print(f"[❌] 聚焦窗口失败: {title}, 错误: {e}")

            print(f"[⚠️] 没有找到匹配的可见窗口: {possible_names}")
        except ImportError:
            print("[❌] pywin32 is not installed. Install it via `pip install pywin32`.")

    elif os_name == "darwin":
        for name in possible_names:
            try:
                subprocess.run(["osascript", "-e", f'tell application "{name}" to activate'], check=True)
                print(f"[✅] macOS聚焦成功: {name}")
                return True
            except subprocess.CalledProcessError:
                continue

    elif os_name == "linux":
        for name in possible_names:
            try:
                # Try wmctrl first
                result = subprocess.run(["wmctrl", "-a", name], check=True)
                if result.returncode == 0:
                    print(f"[✅] Linux聚焦成功: {name}")
                    return True
            except FileNotFoundError:
                print("❌ wmctrl is not installed. Try `sudo apt install wmctrl`.")
                break
            except subprocess.CalledProcessError:
                continue

        # Try xdotool as fallback
        for name in possible_names:
            try:
                subprocess.run(["xdotool", "search", "--name", name, "windowactivate"], check=True)
                print(f"[✅] Linux xdotool聚焦成功: {name}")
                return True
            except:
                continue

    return False


def take_screenshot_b64():
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        shot = sct.grab(monitor)
        img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
        img = img.resize((1280, 720))
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")


def safe_coords(x, y, screen_width, screen_height):
    return max(1, min(screen_width - 1, x)), max(1, min(screen_height - 1, y))


def perform_action(response):
    global screenshot_requested
    actions = response.get("actions", [])
    TARGET_W, TARGET_H = 1280, 720
    screen_w, screen_h = pyautogui.size()
    scale_x = screen_w / TARGET_W
    scale_y = screen_h / TARGET_H

    def scale_coords(coord):
        x = int(coord["x"] * scale_x)
        y = int(coord["y"] * scale_y)
        return safe_coords(x, y, screen_w, screen_h)

    for action in actions:
        try:
            act = action["action"]
            params = action.get("params", {})

            if act in ["left_click", "double_click", "triple_click", "right_click"]:
                x, y = scale_coords(params)
                pyautogui.moveTo(x, y)

                click_config = {
                    "left_click": ("left", 1),
                    "double_click": ("left", 2),
                    "triple_click": ("left", 3),
                    "right_click": ("right", 1),
                }

                button, clicks = click_config[act]
                pyautogui.click(button=button, clicks=clicks, interval=0.1)

            elif act == 'click':
                # Consider it as left click
                x, y = scale_coords(params)
                pyautogui.moveTo(x, y)
                pyautogui.click(button='left')

            elif act == "mouse_move":
                x, y = scale_coords(params)
                pyautogui.moveTo(x, y, duration=0.1)

            elif act == "left_click_drag":
                x1, y1 = scale_coords(params["from"])
                x2, y2 = scale_coords(params["to"])
                pyautogui.moveTo(x1, y1)
                pyautogui.mouseDown()
                pyautogui.moveTo(x2, y2, duration=0.3)
                pyautogui.mouseUp()

            elif act == "left_mouse_down":
                pyautogui.mouseDown()
            elif act == "left_mouse_up":
                pyautogui.mouseUp()

            elif act == "key":
                pyautogui.press(params["text"])

            elif act == "key_combo":
                keys = params.get("keys", [])
                if keys:
                    pyautogui.hotkey(*keys)

            elif act == "type":
                if params.get("replace", False):
                    pyautogui.hotkey("ctrl", "a" if sys.platform != "darwin" else "command")
                    pyautogui.press("backspace")

                type_unicode_smart(params["text"], delay=0.05)

            elif act == "hold_key":
                pyautogui.keyDown(params["text"])
                time.sleep(float(params.get("duration", 1.0)))
                pyautogui.keyUp(params["text"])

            elif act == "scroll":
                x, y = scale_coords({"x": params["x"], "y": params["y"]})
                pyautogui.moveTo(x, y, duration=0.1)
                direction = params.get("scroll_direction", "down")
                amount = params.get("scroll_amount", 3)
                if direction == "down":
                    pyautogui.scroll(-100 * amount)
                elif direction == "up":
                    pyautogui.scroll(100 * amount)
                elif direction == "left":
                    pyautogui.hscroll(-100 * amount)
                elif direction == "right":
                    pyautogui.hscroll(100 * amount)

            elif act == "wait":
                time.sleep(params.get("duration", 1))

            elif act == "launch_browser":
                webbrowser.open(params["url"])

            elif act == "launch_app":
                launch_application(params["app_name"])

            elif act == "focus_app":
                focus_app(params["app_name"])

            elif act == "tool_use":
                print(f"🛠️ Tool requested: {params}")

            elif act == "request_screenshot":
                screenshot_requested = True

            elif act == "subtask_completed":
                print("✅ Subtask completed.")

            elif act == "subtask_failed":
                print("❌ Subtask failed.")

            else:
                print(f"⚠️ Unknown action: {act}")
        except Exception as e:
            print("❌ Exception in perform_action:", e)


def get_next_step():
    global screenshot_requested
    url = os.getenv('NEURALAGENT_API_URL') + '/aiagent/' + os.getenv('NEURALAGENT_THREAD_ID') + '/next_step'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + os.getenv('NEURALAGENT_USER_ACCESS_TOKEN'),
    }

    interactive_elements = ui_extraction.extract_interactive_elements()
    running_apps = ui_extraction.get_running_apps()

    # Automatically trigger screenshot if WebView is present
    has_webview = any(e.get("type") == "PossibleWebView" for e in interactive_elements)
    should_send_screenshot = screenshot_requested or has_webview

    payload = {
        'current_os': 'MacOS' if platform.system() == 'darwin' else platform.system(),
        'current_interactive_elements': interactive_elements,
        'current_running_apps': running_apps,
    }

    if should_send_screenshot:
        payload['screenshot_b64'] = take_screenshot_b64()
        screenshot_requested = False

    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code in (200, 201, 202):
            return response.json()
    except Exception as e:
        print(f"[❌] Error sending next step request: {e}")

    return None


def get_current_subtask():
    url = os.getenv('NEURALAGENT_API_URL') + '/aiagent/' + os.getenv('NEURALAGENT_THREAD_ID') + '/current_subtask'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + os.getenv('NEURALAGENT_USER_ACCESS_TOKEN'),
    }
    payload = {
        'current_os': 'MacOS' if platform.system() == 'darwin' else platform.system(),
        'current_interactive_elements': ui_extraction.extract_interactive_elements(),
        'current_running_apps': ui_extraction.get_running_apps(),
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code in (200, 201, 202):
            return response.json()
    except:
        pass
    return None


async def main_loop():
    while True:
        current_subtask_response = get_current_subtask()
        if not current_subtask_response:
            continue

        if current_subtask_response.get('action') == 'task_completed':
            break

        action_response = get_next_step()
        print("NeuralAgent Next Step Response:", action_response)

        if not action_response:
            continue

        if any(a['action'] in ['task_completed', 'subtask_failed'] for a in action_response.get('actions', [])):
            break

        perform_action(action_response)


if __name__ == "__main__":
    asyncio.run(main_loop())
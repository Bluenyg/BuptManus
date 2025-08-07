import os
import time
import requests
import logging

# LangChain's tool decorator
from langchain_core.tools import tool

# --- Correctly import from your existing project structure ---
# This assumes your project is run from a context where 'src' is a top-level package.
from src.desktop_agent.aiagent.main import perform_action, take_screenshot_b64
from src.desktop_agent.aiagent.ui_extraction import (
    extract_interactive_elements,
    get_running_apps,
    get_os,  # You need to add this helper to ui_extraction.py (see instructions below)
)

logger = logging.getLogger(__name__)


def _execute_desktop_agent_task(task_description: str) -> str:
    """
    Internal logic to orchestrate a full task with the remote desktop agent.
    This is the core implementation called by the LangChain tool.
    """
    API_URL = os.getenv("NEURALAGENT_API_URL")

    TOKEN = os.getenv("NEURALAGENT_USER_ACCESS_TOKEN")

    if not API_URL or not TOKEN:
        return "错误: 必须在环境变量中设置 NEURALAGENT_API_URL 和 NEURALAGENT_USER_ACCESS_TOKEN。"

    HEADERS = {"Content-Type": "application/json", "Authorization": f"Bearer {TOKEN}"}

    # 1. Create Task Thread via API
    try:
        logger.info(f"Creating thread for task: '{task_description}'")
        create_url = f"{API_URL}/apps/threads"
        create_payload = {"task": task_description}
        response = requests.post(create_url, json=create_payload, headers=HEADERS)
        response.raise_for_status()
        data = response.json()

        if data.get("type") != "desktop_task":
            return f"Task classified as '{data.get('type')}', not a desktop task. Agent will not run."

        thread_id = data.get("thread_id")
        if not thread_id:
            return "Error: API did not return a thread_id upon task creation."
        logger.info(f"Thread created with ID: {thread_id}")

    except requests.RequestException as e:
        error_msg = f"API Error creating task thread: {e.response.text if e.response else str(e)}"
        logger.error(error_msg)
        return error_msg

    # 2. Main Execution Loop
    max_steps = 30  # Safety break to prevent infinite loops
    for step in range(max_steps):
        try:
            logger.info(f"--- [Thread: {thread_id}] Step {step + 1}/{max_steps} ---")
            time.sleep(1.5)  # Wait for UI to settle after the last action

            # 2a. Get Current Subtask
            subtask_url = f"{API_URL}/aiagent/{thread_id}/current_subtask"
            desktop_state_payload = {
                'current_os': get_os(),
                'current_interactive_elements': extract_interactive_elements(),
                'current_running_apps': get_running_apps(),
            }
            subtask_response = requests.post(subtask_url, json=desktop_state_payload, headers=HEADERS)
            subtask_response.raise_for_status()
            subtask_data = subtask_response.json()

            if subtask_data.get("action") == "task_completed":
                success_msg = f"Task '{task_description}' completed successfully."
                logger.info(f"[{thread_id}] {success_msg}")
                return success_msg

            logger.info(f"[{thread_id}] Current Subtask: {subtask_data.get('subtask_text')}")

            # 2b. Get Next Step Actions from the agent
            next_step_url = f"{API_URL}/aiagent/{thread_id}/next_step"
            next_step_payload = {
                'current_os': get_os(),
                'current_interactive_elements': extract_interactive_elements(),
                'current_running_apps': get_running_apps(),
                'screenshot_b64': take_screenshot_b64(),
            }
            actions_response = requests.post(next_step_url, json=next_step_payload, headers=HEADERS)
            actions_response.raise_for_status()
            actions_data = actions_response.json()

            action_names = [a.get('action', 'unknown') for a in actions_data.get('actions', [])]
            logger.info(f"[{thread_id}] Agent wants to perform: {action_names}")

            # 2c. Check for terminal actions
            actions = actions_data.get("actions", [])
            if not actions or any(a.get('action') == 'task_completed' for a in actions):
                return f"Task '{task_description}' marked as completed by agent."
            if any(a.get('action') in ['subtask_failed', 'task_failed'] for a in actions):
                return f"Task '{task_description}' failed as per agent's instruction."

            # 2d. Perform the actions locally
            perform_action(actions_data)

        except requests.RequestException as e:
            error_msg = f"[{thread_id}] API Error during execution loop: {e.response.text if e.response else str(e)}"
            return error_msg
        except Exception as e:
            local_error_msg = f"[{thread_id}] Local execution error during step {step + 1}: {e}"
            logger.error(local_error_msg, exc_info=True)
            return local_error_msg

    timeout_msg = f"Task '{task_description}' timed out after {max_steps} steps."
    logger.warning(f"[{thread_id}] {timeout_msg}")
    return timeout_msg


# ==============================================================================
#  THE LANGCHAIN TOOL DEFINITION
# ==============================================================================

@tool
def remote_desktop_agent(task_description: str) -> str:
    """
    Use this tool to perform complex tasks on a user's desktop computer. It can open applications, type text, click buttons, and interact with the graphical user interface (GUI).
    This is the best tool for any request that involves manipulating files on the desktop, using specific software (like a browser, text editor, or IDE), or completing a workflow that requires GUI interaction.
    For example: "open the browser and search for 'LangChain'", "find the file named 'report.docx' and open it", or "write 'hello world' in Notepad".
    The input must be a single string which is a clear, detailed, and specific instruction of the task to be performed.
    """
    return _execute_desktop_agent_task(task_description)


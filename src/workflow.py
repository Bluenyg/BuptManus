import logging
from src.config import TEAM_MEMBERS
from src.graph import build_graph

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Default level is INFO
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def enable_debug_logging():
    """Enable debug level logging for more detailed execution information."""
    logging.getLogger("src").setLevel(logging.DEBUG)


logger = logging.getLogger(__name__)

# Create the graph
graph = build_graph()


# --- 修改后的 run_agent_workflow 函数 ---
def run_agent_workflow(user_input: str, image_path: str = None, debug: bool = False):
    """
    运行Agent工作流。

    Args:
        user_input: 用户的文本请求。
        image_path: (可选) 用户提供的图片文件路径。
        debug: 是否开启调试日志。

    Returns:
        工作流完成后的最终状态。
    """
    if not user_input:
        raise ValueError("用户输入不能为空")

    if debug:
        enable_debug_logging()

    logger.info(f"工作流启动，用户输入: {user_input}")
    if image_path:
        logger.info(f"包含图片输入: {image_path}")

    # --- 多模态消息构建逻辑 ---
    message_content = []
    image_base64_str = None

    # 1. 添加文本部分
    message_content.append({"type": "text", "text": user_input})

    # 2. 如果有图片，进行Base64编码并添加到消息中
    if image_path:
        try:
            image_path_obj = Path(image_path)
            if not image_path_obj.exists():
                raise FileNotFoundError(f"图片文件未找到: {image_path}")

            # 根据文件扩展名确定MIME类型
            mime_type_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".gif": "image/gif"}
            mime_type = mime_type_map.get(image_path_obj.suffix.lower())
            if not mime_type:
                raise ValueError("不支持的图片格式，请使用 JPG, PNG, GIF。")

            with open(image_path_obj, "rb") as image_file:
                image_base64_str = base64.b64encode(image_file.read()).decode('utf-8')

            message_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime_type};base64,{image_base64_str}"
                }
            })
        except Exception as e:
            logger.error(f"处理图片时出错: {e}")
            # 如果图片处理失败，可以选择抛出异常或仅继续处理文本
            raise e

    # 构建初始状态
    initial_state = {
        "TEAM_MEMBERS": TEAM_MEMBERS,
        "messages": [HumanMessage(content=message_content)],  # <-- 关键：content现在是一个列表
        "image_base64": image_base64_str,  # <-- 将图片数据存入状态
        "deep_thinking_mode": True,
        "search_before_planning": False,
    }

    result = graph.invoke(initial_state)
    logger.debug(f"最终工作流状态: {result}")
    logger.info("工作流成功完成")
    return result

if __name__ == "__main__":
    print(graph.get_graph().draw_mermaid())

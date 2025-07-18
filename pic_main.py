import requests
import json
import os

# --- 配置您的测试 ---

# 1. FastAPI服务器的地址和端点
API_ENDPOINT_URL = "http://127.0.0.1:8000/api/chat/stream"

# 2. 指定您要测试的图片文件的路径
#    确保这张图片与此脚本在同一个文件夹，或者提供正确的完整路径
IMAGE_FILE_PATH = "data/shanghai.jpg"

# 3. 编写您想要问的关于这张图片的问题
USER_QUERY = "这张图片里有什么？请帮我基于图片内容，生成一个详细的旅行计划。"

# 4. 其他表单字段 (根据您的API定义)
DEBUG_MODE = True
DEEP_THINKING_MODE = True
SEARCH_BEFORE_PLANNING = False


# --------------------

def run_test():
    """
    主执行函数，用于启动多模态输入的工作流测试。
    """
    print("--- 开始多模态输入流式测试 ---")

    # 检查图片文件是否存在
    if not os.path.exists(IMAGE_FILE_PATH):
        print(f"\n错误：测试图片未找到！")
        print(f"请确保名为 '{IMAGE_FILE_PATH}' 的图片文件与本脚本在同一个目录下。")
        return

    # 1. 准备 messages 字段，它必须是一个JSON字符串
    messages_payload = json.dumps([
        {"role": "user", "content": USER_QUERY}
    ])

    # 2. 准备 multipart/form-data
    #    - 'files' 字典用于上传文件
    #    - 'data' 字典用于传递其他表单字段
    form_data = {
        "messages": messages_payload,
        "debug": str(DEBUG_MODE),
        "deep_thinking_mode": str(DEEP_THINKING_MODE),
        "search_before_planning": str(SEARCH_BEFORE_PLANNING),
    }

    try:
        # 3. 使用二进制模式打开图片文件
        with open(IMAGE_FILE_PATH, "rb") as image_file:
            files_payload = {"image": (os.path.basename(IMAGE_FILE_PATH), image_file, "image/jpeg")}

            print(f"正在向 {API_ENDPOINT_URL} 发送请求...")
            print(f"问题: {USER_QUERY}")
            print(f"图片: {IMAGE_FILE_PATH}")
            print("-" * 30)

            # 4. 发送POST请求，并设置 stream=True 来接收流式响应
            with requests.post(API_ENDPOINT_URL, data=form_data, files=files_payload, stream=True) as response:
                response.raise_for_status()  # 如果请求失败 (例如 4xx 或 5xx 错误)，则抛出异常

                # 5. 迭代处理SSE (Server-Sent Events)
                for line in response.iter_lines():
                    if line:
                        decoded_line = line.decode('utf-8')
                        # SSE事件通常以 "event: " 和 "data: " 开头
                        if decoded_line.startswith('event:'):
                            print(f"\n收到事件 -> {decoded_line.split('event: ')[1]}")
                        elif decoded_line.startswith('data:'):
                            # 解析 data 字段的 JSON 内容
                            json_data = decoded_line.split('data: ')[1]
                            try:
                                data_obj = json.loads(json_data)
                                print(f"  数据: {json.dumps(data_obj, indent=2, ensure_ascii=False)}")
                            except json.JSONDecodeError:
                                print(f"  原始数据 (非JSON): {json_data}")
                        else:
                            print(f"收到未知行: {decoded_line}")


    except requests.exceptions.RequestException as e:
        print(f"\n请求失败: {e}")
        print("请确保您的FastAPI服务器正在运行，并且地址和端口正确。")
    except Exception as e:
        print(f"\n测试过程中发生未知错误: {e}")


if __name__ == "__main__":
    run_test()
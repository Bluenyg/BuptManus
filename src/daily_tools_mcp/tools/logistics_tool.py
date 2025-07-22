# src/tools/logistics_tool.py

import os
import json
import hashlib
import requests
import logging
from typing import Dict, Any
from .base_tool import BaseTool
from src.config import KUAIDI100_API_KEY, CUSTOMER_ID # 引用统一的配置

logger = logging.getLogger(__name__)

# --- 保留健壮的快递公司名称映射 ---
COURIER_MAP = {
    # 顺丰速运 (SF Express)
    "shunfeng": "shunfeng", "顺丰": "shunfeng", "顺丰速运": "shunfeng", "sf": "shunfeng", "sf express": "shunfeng",
    # 中通快递 (ZTO Express)
    "zhongtong": "zhongtong", "中通": "zhongtong", "zto": "zhongtong",
    # 圆通速递 (YTO Express)
    "yuantong": "yuantong", "圆通": "yuantong", "yto": "yuantong",
    # 申通快递 (STO Express)
    "shentong": "shentong", "申通": "shentong", "sto": "shentong",
    # 韵达快递 (Yunda Express)
    "yunda": "yunda", "韵达": "yunda",
    # 京东物流
    "jd": "jd", "jingdong": "jd", "京东": "jd", "京东物流": "jd",
}

class LogisticsTool(BaseTool):
    """物流跟踪工具，继承自 BaseTool"""

    def __init__(self):
        # 初始化时不再直接读取环境变量，而是依赖配置文件
        super().__init__()

    def get_name(self) -> str:
        return "logistics_tracking"

    def get_description(self) -> str:
        return "查询包裹的实时物流信息。你需要提供快递单号(tracking_number)、快递公司(courier_company)和收/寄件人手机号(phone_number)。"

    def get_input_schema(self) -> Dict[str, Any]:
        """
        定义工具的输入参数。这里的 'properties' 键名需要与 execute 方法中从 'arguments' 字典里取的键名一致。
        """
        return {
            "type": "object",
            "properties": {
                "tracking_number": {"type": "string", "description": "要查询的快递包裹单号。"},
                "courier_company": {"type": "string", "description": "快递公司名称，例如：顺丰, 中通, 圆通, 申通, 韵达等,但注意要全部转为小写字母，例如：shunfeng，zhongtong，yunda，yuantong，yuantong等"},
                "phone_number": {"type": "string", "description": "收件人或寄件人的手机号码，用于验证（通常是后四位）。"}
            },
            "required": ["tracking_number", "courier_company"] # 手机号通常是可选的
        }

    def _get_courier_code(self, human_readable_name: str) -> str:
        """辅助函数：将用户易读的公司名转为API代码。"""
        if not human_readable_name:
            return None
        normalized_name = str(human_readable_name).lower().strip()
        return COURIER_MAP.get(normalized_name)

    async def execute(self, arguments: Dict[str, Any]) -> str:
        """
        执行物流跟踪。
        此方法签名保持不变，以兼容您现有的框架。
        内部逻辑已更新为新版API调用方式。
        """
        # --- 0. 验证和提取参数 ---
        try:
            self.validate_arguments(arguments, self.get_input_schema()["required"])
            tracking_number = arguments["tracking_number"]
            courier_company = arguments["courier_company"]
            phone_number = arguments.get("phone_number", "") # phone_number 作为可选参数
        except ValueError as e:
            return f"参数错误: {e}"

        # --- 1. 获取 API 凭证 ---
        api_key = KUAIDI100_API_KEY
        customer_id = CUSTOMER_ID
        if not api_key or not customer_id:
            logger.error("未配置快递100的API凭证。")
            return "错误: 必须配置 KUAIDI100_API_KEY 和 CUSTOMER_ID。"

        # --- 2. 转换快递公司名称为API代码 ---
        com_code = self._get_courier_code(courier_company)
        if not com_code:
            logger.warning(f"无法映射快递公司 '{courier_company}' 到有效的API代码。")
            return f"错误: 不支持或未知的快递公司: '{courier_company}'。"
        logger.info(f"映射 '{courier_company}' 到 API 代码: '{com_code}'")

        # --- 3. 构造请求参数 (采用新版格式) ---
        url = 'https://poll.kuaidi100.com/poll/query.do'
        param = {
            'com': com_code,
            'num': tracking_number,
            'phone': phone_number,
            'resultv2': '1',
            'show': '0',
            'order': 'desc'
        }
        param_str = json.dumps(param)

        # --- 4. 生成签名 ---
        temp_sign = param_str + api_key + customer_id
        md = hashlib.md5()
        md.update(temp_sign.encode())
        sign = md.hexdigest().upper()

        request_data = {
            'customer': customer_id,
            'param': param_str,
            'sign': sign
        }

        # --- 5. 发送请求 ---
        logger.info(f"正在为运单号: {tracking_number} 发送请求")
        try:
            # 在异步函数中使用同步的requests，通常不推荐，但为了保持逻辑一致性暂时保留
            # 生产环境建议替换为 httpx.AsyncClient
            response = requests.post(url, data=request_data, timeout=10)
            response.raise_for_status()
            logger.info(f"成功接收到 {tracking_number} 的响应")
            return response.text
        except requests.exceptions.RequestException as e:
            logger.error(f"为 {tracking_number} 请求API时失败: {e}", exc_info=True)
            return f"API 请求期间出错: {e}"
        except Exception as e:
            logger.error(f"物流查询时发生未知错误: {e}", exc_info=True)
            return f"查询出错: {e}"
import json
import hashlib
import requests
import asyncio
from typing import Dict, Any
from .base_tool import BaseTool
from src.config import KUAIDI100_API_KEY, CUSTOMER_ID


class LogisticsTool(BaseTool):
    """物流跟踪工具"""

    def __init__(self):
        super().__init__(
            name="track_logistics",
            description="查询快递物流跟踪信息",
            input_schema={
                "type": "object",
                "properties": {
                    "com": {
                        "type": "string",
                        "description": "快递公司代码，小写格式（如：'yuantong', 'shunfeng'）"
                    },
                    "num": {
                        "type": "string",
                        "description": "快递单号，最大长度32个字符"
                    },
                    "phone": {
                        "type": "string",
                        "description": "收件人或寄件人手机号，可以是后四位数字",
                        "default": ""
                    },
                    "ship_from": {
                        "type": "string",
                        "description": "出发地，格式：'省份-城市-区县'",
                        "default": ""
                    },
                    "ship_to": {
                        "type": "string",
                        "description": "目的地，格式：'省份-城市-区县'",
                        "default": ""
                    }
                },
                "required": ["com", "num"]
            }
        )

    async def execute(self, arguments: Dict[str, Any]) -> str:
        """执行物流跟踪查询"""
        self.validate_arguments(arguments)

        com = arguments.get("com", "")
        num = arguments.get("num", "")
        phone = arguments.get("phone", "")
        ship_from = arguments.get("ship_from", "")
        ship_to = arguments.get("ship_to", "")

        return await self._track_logistics(com, num, phone, ship_from, ship_to)

    async def _track_logistics(self, com: str, num: str, phone: str = "",
                               ship_from: str = "", ship_to: str = "") -> str:
        """内部物流跟踪逻辑"""
        api_key = KUAIDI100_API_KEY
        customer_id = CUSTOMER_ID

        if not api_key or not customer_id:
            return "Error: KUAIDI100_API_KEY and CUSTOMER_ID must be set in config."

        url = 'https://poll.kuaidi100.com/poll/query.do'

        param = {
            'com': com,
            'num': num,
            'phone': phone,
            'from': ship_from,
            'to': ship_to,
            'resultv2': '1',
            'show': '0',
            'order': 'desc'
        }
        param_str = json.dumps(param)

        # 生成签名
        temp_sign = param_str + api_key + customer_id
        md = hashlib.md5()
        md.update(temp_sign.encode())
        sign = md.hexdigest().upper()

        request_data = {
            'customer': customer_id,
            'param': param_str,
            'sign': sign
        }

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(url, data=request_data, timeout=10)
            )
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            return f"Error during API request: {e}"

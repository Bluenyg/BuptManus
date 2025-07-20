import os
import json
import hashlib
import requests
from typing import Dict, Any
from .base_tool import BaseTool


class LogisticsTool(BaseTool):
    """物流跟踪工具"""

    def __init__(self):
        # 从环境变量或配置文件中获取 API 密钥
        self.api_key = os.getenv('KUAIDI100_API_KEY', 'your_api_key_here')
        self.customer_id = os.getenv('CUSTOMER_ID', 'your_customer_id_here')
        super().__init__()

    def get_name(self) -> str:
        return "track_logistics"

    def get_description(self) -> str:
        return "跟踪物流信息，支持多家快递公司"

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "com": {
                    "type": "string",
                    "description": "快递公司代码，如：shunfeng, zhongtong, yuantong"
                },
                "num": {
                    "type": "string",
                    "description": "快递单号"
                },
                "phone": {
                    "type": "string",
                    "description": "收件人或寄件人手机号（可选）",
                    "default": ""
                },
                "ship_from": {
                    "type": "string",
                    "description": "寄件地（可选）",
                    "default": ""
                },
                "ship_to": {
                    "type": "string",
                    "description": "收件地（可选）",
                    "default": ""
                }
            },
            "required": ["com", "num"]
        }

    async def execute(self, arguments: Dict[str, Any]) -> str:
        """执行物流跟踪"""
        try:
            # 验证必需参数
            self.validate_arguments(arguments, ["com", "num"])

            com = arguments["com"]
            num = arguments["num"]
            phone = arguments.get("phone", "")
            ship_from = arguments.get("ship_from", "")
            ship_to = arguments.get("ship_to", "")

            # 构造请求参数
            param = {
                "com": com,
                "num": num,
                "phone": phone,
                "from": ship_from,
                "to": ship_to
            }

            # 生成签名
            param_json = json.dumps(param, separators=(',', ':'))
            sign_str = f"{param_json}{self.api_key}{self.customer_id}"
            sign = hashlib.md5(sign_str.encode('utf-8')).hexdigest().upper()

            # 构造请求数据
            data = {
                "customer": self.customer_id,
                "sign": sign,
                "param": param_json
            }

            # 发送请求
            response = requests.post(
                "https://poll.kuaidi100.com/poll/query.do",
                data=data,
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("message") == "ok":
                    return self._format_tracking_result(result)
                else:
                    return f"查询失败: {result.get('message', '未知错误')}"
            else:
                return f"请求失败，状态码: {response.status_code}"

        except Exception as e:
            return f"物流查询出错: {str(e)}"

    def _format_tracking_result(self, result: Dict[str, Any]) -> str:
        """格式化跟踪结果"""
        data = result.get("data", {})

        # 基本信息
        output = f"快递公司: {data.get('com', 'N/A')}\n"
        output += f"快递单号: {data.get('nu', 'N/A')}\n"
        output += f"当前状态: {self._get_status_desc(data.get('state', ''))}\n"
        output += f"是否签收: {'是' if data.get('ischeck') == '1' else '否'}\n\n"

        # 物流轨迹
        traces = data.get("data", [])
        if traces:
            output += "物流轨迹:\n"
            for i, trace in enumerate(traces):
                output += f"{i + 1}. {trace.get('time', 'N/A')} - {trace.get('context', 'N/A')}\n"
        else:
            output += "暂无物流轨迹信息\n"

        return output

    def _get_status_desc(self, state: str) -> str:
        """获取状态描述"""
        status_map = {
            "0": "在途",
            "1": "揽收",
            "2": "疑难",
            "3": "已签收",
            "4": "退签",
            "5": "派件",
            "6": "退回",
            "7": "转单",
            "10": "待清关",
            "11": "清关中",
            "12": "已清关",
            "13": "清关异常",
            "14": "收件人拒签"
        }
        return status_map.get(state, "未知状态")

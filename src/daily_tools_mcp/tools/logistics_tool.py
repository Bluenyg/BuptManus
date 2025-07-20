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
        return "跟踪物流信息，支持多家快递公司。需要提供快递单号、快递公司和手机号码。"

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "tracking_number": {
                    "type": "string",
                    "description": "快递单号"
                },
                "courier_company": {
                    "type": "string",
                    "description": "快递公司名称，如：顺丰、中通、圆通、申通、韵达等"
                },
                "phone_number": {
                    "type": "string",
                    "description": "收件人或寄件人手机号码后四位"
                }
            },
            "required": ["tracking_number", "courier_company", "phone_number"]
        }

    async def execute(self, arguments: Dict[str, Any]) -> str:
        """执行物流跟踪"""
        try:
            # 验证必需参数
            self.validate_arguments(arguments, ["tracking_number", "courier_company", "phone_number"])

            tracking_number = arguments["tracking_number"]
            courier_company = arguments["courier_company"]
            phone_number = arguments["phone_number"]

            # 将快递公司名称转换为代码
            com_code = self._get_courier_code(courier_company)
            if not com_code:
                return f"不支持的快递公司: {courier_company}"

            # 构造请求参数
            param = {
                "com": com_code,
                "num": tracking_number,
                "phone": phone_number
            }

            # 如果没有配置真实的 API 密钥，返回模拟数据
            if self.api_key == 'your_api_key_here' or not self.api_key:
                return self._get_mock_result(tracking_number, courier_company, phone_number)

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

    def _get_courier_code(self, courier_name: str) -> str:
        """将快递公司名称转换为代码"""
        courier_map = {
            "顺丰": "shunfeng",
            "圆通": "yuantong",
            "中通": "zhongtong",
            "申通": "shentong",
            "韵达": "yunda",
            "百世": "huitongkuaidi",
            "天天": "tiantian",
            "京东": "jd",
            "德邦": "debangwuliu",
            "邮政": "ems",
            "EMS": "ems"
        }

        # 精确匹配
        if courier_name in courier_map:
            return courier_map[courier_name]

        # 模糊匹配
        for name, code in courier_map.items():
            if name in courier_name or courier_name in name:
                return code

        return ""

    def _get_mock_result(self, tracking_number: str, courier_company: str, phone_number: str) -> str:
        """返回模拟的物流查询结果"""
        return f"""
📦 物流查询结果

快递公司: {courier_company}
快递单号: {tracking_number}
手机号码: {phone_number}
当前状态: 运输中

🚚 物流轨迹:
1. 2024-01-15 10:30 - 【深圳分拨中心】快件已发出，正在运输途中
2. 2024-01-15 08:15 - 【深圳分拨中心】快件已到达分拨中心
3. 2024-01-14 18:20 - 【深圳南山营业点】快件已揽收

注意: 这是模拟数据，实际使用需要配置真实的快递100 API密钥。
要获取真实数据，请：
1. 注册快递100账号 (https://www.kuaidi100.com)
2. 获取API密钥和客户ID
3. 设置环境变量 KUAIDI100_API_KEY 和 CUSTOMER_ID
"""

    def _format_tracking_result(self, result: Dict[str, Any]) -> str:
        """格式化跟踪结果"""
        data = result.get("data", {})

        # 基本信息
        output = f"📦 物流查询结果\n\n"
        output += f"快递公司: {data.get('com', 'N/A')}\n"
        output += f"快递单号: {data.get('nu', 'N/A')}\n"
        output += f"当前状态: {self._get_status_desc(data.get('state', ''))}\n"
        output += f"是否签收: {'是' if data.get('ischeck') == '1' else '否'}\n\n"

        # 物流轨迹
        traces = data.get("data", [])
        if traces:
            output += "🚚 物流轨迹:\n"
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

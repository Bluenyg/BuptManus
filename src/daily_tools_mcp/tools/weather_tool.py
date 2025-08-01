import json
import requests
import logging
from typing import Dict, Any
from .base_tool import BaseTool
from src.config import AMAP_API_KEY

logger = logging.getLogger(__name__)


class WeatherTool(BaseTool):
    """天气查询工具，继承自 BaseTool"""

    def __init__(self):
        super().__init__()

    def get_name(self) -> str:
        return "weather_query"

    def get_description(self) -> str:
        return "查询指定城市的实时天气信息或天气预报。支持中文城市名称、英文城市名称、城市adcode等多种输入方式。"

    def get_input_schema(self) -> Dict[str, Any]:
        """
        定义工具的输入参数
        """
        return {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市信息，支持以下格式：\n1. 中文城市名：如'北京'、'上海'、'深圳市'、'朝阳区'\n2. 英文城市名：如'Beijing'、'Shanghai'\n3. 城市adcode：如'110000'（北京）、'440300'（深圳）\n4. 可精确到区县级别：如'朝阳区'、'浦东新区'"
                },
                "extensions": {
                    "type": "string",
                    "description": "查询类型：'base'查询实时天气，'all'查询天气预报（未来3天）",
                    "enum": ["base", "all"],
                    "default": "base"
                }
            },
            "required": ["city"]
        }

    def _get_geo_info(self, city_name: str) -> Dict[str, Any]:
        """
        使用高德地图地理编码API获取城市的详细信息
        这样可以支持更灵活的城市名称输入
        """
        if not AMAP_API_KEY:
            return None

        geo_url = 'https://restapi.amap.com/v3/geocode/geo'
        geo_params = {
            'address': city_name,
            'key': AMAP_API_KEY,
            'output': 'JSON'
        }

        try:
            response = requests.get(geo_url, params=geo_params, timeout=10)
            response.raise_for_status()
            geo_data = response.json()

            if geo_data.get('status') == '1' and geo_data.get('geocodes'):
                geocode = geo_data['geocodes'][0]
                return {
                    'adcode': geocode.get('adcode'),
                    'formatted_address': geocode.get('formatted_address'),
                    'city': geocode.get('city'),
                    'district': geocode.get('district')
                }
        except Exception as e:
            logger.warning(f"获取地理编码信息失败: {e}")

        return None

    def _validate_and_normalize_city(self, city: str) -> str:
        """
        验证并标准化城市输入
        高德天气API支持多种城市输入格式，这里做基本的预处理
        """
        if not city:
            raise ValueError("城市参数不能为空")

        city = city.strip()

        # 如果是纯数字，可能是adcode
        if city.isdigit():
            return city

        # 对于中文城市名，可以尝试获取更准确的adcode
        geo_info = self._get_geo_info(city)
        if geo_info and geo_info.get('adcode'):
            logger.info(f"将城市名称 '{city}' 转换为adcode: {geo_info['adcode']}")
            return geo_info['adcode']

        # 如果获取不到地理编码信息，直接使用原始输入
        # 高德API通常能够识别大部分城市名称
        return city

    async def execute(self, arguments: Dict[str, Any]) -> str:
        """
        执行天气查询
        """
        try:
            # 提取参数
            city = arguments.get("city")
            extensions = arguments.get("extensions", "base")

            # 验证和标准化城市输入
            normalized_city = self._validate_and_normalize_city(city)

        except ValueError as e:
            return f"参数错误: {e}"

        # 获取API密钥
        api_key = AMAP_API_KEY
        if not api_key:
            logger.error("未配置高德地图的API密钥。")
            return "错误: 必须配置 AMAP_API_KEY。请在环境变量中设置您的高德地图API密钥。"

        # 构造请求参数
        url = 'https://restapi.amap.com/v3/weather/weatherInfo'
        params = {
            'city': normalized_city,
            'key': api_key,
            'extensions': extensions,
            'output': 'JSON'
        }

        # 发送请求
        logger.info(f"正在查询城市: {city} (标准化后: {normalized_city}) 的天气信息")
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            # 解析响应
            response_data = response.json()

            if response_data.get('status') == '1':
                # API调用成功
                lives = response_data.get('lives', [])
                forecasts = response_data.get('forecasts', [])

                if lives:
                    # 实时天气
                    weather_info = lives[0]
                    return self._format_live_weather(weather_info)
                elif forecasts:
                    # 天气预报
                    forecast_info = forecasts[0]
                    return self._format_forecast_weather(forecast_info)
                else:
                    return f"未找到城市 '{city}' 的天气信息，请检查城市名称是否正确。"

            else:
                error_msg = response_data.get('info', '未知错误')
                error_code = response_data.get('infocode', '')

                # 针对常见错误提供更友好的提示
                if error_code == '10003':
                    return f"查询失败: 请检查城市名称 '{city}' 是否正确。建议使用完整的城市名称，如'北京市'、'上海市'等。"
                elif error_code == '10001':
                    return "查询失败: API密钥无效，请检查配置。"
                else:
                    logger.error(f"天气API返回错误: {error_msg} (代码: {error_code})")
                    return f"天气API错误: {error_msg}"

        except requests.exceptions.RequestException as e:
            logger.error(f"天气API请求失败: {e}", exc_info=True)
            return f"网络请求失败: {e}。请检查网络连接后重试。"
        except json.JSONDecodeError as e:
            logger.error(f"解析天气API响应失败: {e}", exc_info=True)
            return f"解析API响应出错: {e}"
        except Exception as e:
            logger.error(f"天气查询时发生未知错误: {e}", exc_info=True)
            return f"查询出错: {e}"

    def _format_live_weather(self, weather_info: Dict[str, Any]) -> str:
        """格式化实时天气信息"""
        city = weather_info.get('city', '未知城市')
        adcode = weather_info.get('adcode', '')
        weather = weather_info.get('weather', '未知')
        temperature = weather_info.get('temperature', '未知')
        wind_direction = weather_info.get('winddirection', '未知')
        wind_power = weather_info.get('windpower', '未知')
        humidity = weather_info.get('humidity', '未知')
        report_time = weather_info.get('reporttime', '未知时间')

        # 添加天气状况的emoji
        weather_emoji = self._get_weather_emoji(weather)

        formatted = f"""📍 {city} 实时天气{f' (代码:{adcode})' if adcode else ''}

{weather_emoji} 天气状况: {weather}
🌡️ 温度: {temperature}°C
💨 风向: {wind_direction}
💪 风力: {wind_power}级
💧 湿度: {humidity}%
⏰ 数据更新: {report_time}

💡 数据来源: 高德地图天气API"""

        return formatted

    def _format_forecast_weather(self, forecast_info: Dict[str, Any]) -> str:
        """格式化天气预报信息"""
        city = forecast_info.get('city', '未知城市')
        adcode = forecast_info.get('adcode', '')
        casts = forecast_info.get('casts', [])

        formatted = f"📍 {city} 天气预报{f' (代码:{adcode})' if adcode else ''}\n\n"

        for i, cast in enumerate(casts):
            date = cast.get('date', '未知日期')
            week = cast.get('week', '')
            day_weather = cast.get('dayweather', '未知')
            night_weather = cast.get('nightweather', '未知')
            day_temp = cast.get('daytemp', '未知')
            night_temp = cast.get('nighttemp', '未知')
            day_wind = cast.get('daywind', '未知')
            day_power = cast.get('daypower', '未知')
            night_wind = cast.get('nightwind', '未知')
            night_power = cast.get('nightpower', '未知')

            # 确定日期标签
            if i == 0:
                day_label = "今天"
            elif i == 1:
                day_label = "明天"
            elif i == 2:
                day_label = "后天"
            else:
                day_label = f"{date}"

            # 添加天气emoji
            day_emoji = self._get_weather_emoji(day_weather)
            night_emoji = self._get_weather_emoji(night_weather)

            formatted += f"""📅 {day_label} ({date} {week})
☀️ 白天: {day_emoji} {day_weather} {day_temp}°C
🌙 夜间: {night_emoji} {night_weather} {night_temp}°C  
💨 风向风力: 白天{day_wind}{day_power}级 / 夜间{night_wind}{night_power}级

"""

        formatted += "💡 数据来源: 高德地图天气API"
        return formatted.strip()

    def _get_weather_emoji(self, weather: str) -> str:
        """根据天气状况返回对应的emoji"""
        emoji_map = {
            '晴': '☀️', '多云': '⛅', '阴': '☁️',
            '小雨': '🌦️', '中雨': '🌧️', '大雨': '⛈️', '暴雨': '⛈️',
            '雷阵雨': '⛈️', '阵雨': '🌦️',
            '小雪': '🌨️', '中雪': '❄️', '大雪': '❄️', '暴雪': '❄️',
            '雨夹雪': '🌨️', '雾': '🌫️', '霾': '😷',
            '沙尘暴': '💨', '浮尘': '💨', '扬沙': '💨'
        }

        for key, emoji in emoji_map.items():
            if key in weather:
                return emoji
        return '🌤️'  # 默认emoji

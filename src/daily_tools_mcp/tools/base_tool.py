from abc import ABC, abstractmethod
from typing import Dict, Any
import json


class BaseTool(ABC):
    """MCP工具基类"""

    def __init__(self):
        self.name = self.get_name()
        self.description = self.get_description()
        self.input_schema = self.get_input_schema()

    @abstractmethod
    def get_name(self) -> str:
        """获取工具名称"""
        pass

    @abstractmethod
    def get_description(self) -> str:
        """获取工具描述"""
        pass

    @abstractmethod
    def get_input_schema(self) -> Dict[str, Any]:
        """获取输入参数架构"""
        pass

    @abstractmethod
    async def execute(self, arguments: Dict[str, Any]) -> str:
        """执行工具"""
        pass

    def validate_arguments(self, arguments: Dict[str, Any], required_fields: list) -> None:
        """验证参数"""
        for field in required_fields:
            if field not in arguments:
                raise ValueError(f"Missing required field: {field}")

from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseTool(ABC):
    """工具基类"""

    def __init__(self, name: str, description: str, input_schema: Dict[str, Any]):
        self.name = name
        self.description = description
        self.input_schema = input_schema

    @abstractmethod
    async def execute(self, arguments: Dict[str, Any]) -> str:
        """执行工具逻辑"""
        pass

    def validate_arguments(self, arguments: Dict[str, Any]) -> bool:
        """验证参数（可选实现）"""
        required_fields = self.input_schema.get("required", [])
        for field in required_fields:
            if field not in arguments:
                raise ValueError(f"Missing required argument: {field}")
        return True

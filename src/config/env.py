import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 思考型大语言模型部署 (for complex reasoning tasks)
REASONING_MODEL = os.getenv("REASONING_MODEL", "o1-mini")
REASONING_BASE_URL = os.getenv("REASONING_BASE_URL")
REASONING_API_KEY = os.getenv("REASONING_API_KEY")

# 非思考型大语言模型部署 (for straightforward tasks)
BASIC_MODEL = os.getenv("BASIC_MODEL", "gpt-4o")
BASIC_BASE_URL = os.getenv("BASIC_BASE_URL")
BASIC_API_KEY = os.getenv("BASIC_API_KEY")

# 视觉模型部署 (for tasks requiring visual understanding)
VL_MODEL = os.getenv("VL_MODEL", "gpt-4o")
VL_BASE_URL = os.getenv("VL_BASE_URL")
VL_API_KEY = os.getenv("VL_API_KEY")

# Chrome Instance configuration
CHROME_INSTANCE_PATH = os.getenv("CHROME_INSTANCE_PATH")

#快递的API_KEY
KUAIDI100_API_KEY = os.getenv("KUAIDI100_API_KEY")
CUSTOMER_ID = os.getenv("CUSTOMER_ID")

#数据库的url
DATABASE_URL = os.getenv("DATABASE_URL")

AMAP_API_KEY= os.getenv("AMAP_API_KEY")

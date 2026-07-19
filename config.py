"""
统一配置管理
"""
from pathlib import Path

class Config:
    """配置类"""
    
    # ========== 路径配置 ==========
    BASE_DIR = Path(__file__).parent.absolute()
    
    # 产品数据目录（所有产品相关数据）
    PRODUCTS_DIR = BASE_DIR / "products"
    
    # 导出文档目录（在 products 下）
    EXPORTS_DIR = PRODUCTS_DIR / "exports"
    
    # 日志目录
    LOGS_DIR = BASE_DIR / "logs"
    
    # ========== 登录配置 ==========
    LOGIN_URL = "https://idp.amwaylive.com/auth/oauth2/default/v1/authorize?response_type=id_token&nonce=b9vqIDM1AbTRwQfTjlkJ1uYo41Zm8BoxgyLU5vaALZjW9&state=4StsyD3r4512VL5TFCPcJiwhgwaGBclXPFek4bXVCf0L9JFtIYBTz52HfqCbBdor&site=amwayjapan&response_mode=form_post&client_id=LI_Trusted_Client&scope=extended&redirect_uri=https://api.amwaylive.com/api/v2/amwayjapan/bff-login-callback&code_challenge=mmwn6l2uYwyPm1bijJcSY8KO0f0TsrJhImUs6qCbsgOfMxzT9I0brY57ElC4Yyld&code_challenge_method=PLAIN"
    USERNAME = "nieshuqing@126.com"
    PASSWORD = "pow897same536@a"
    
    # ========== 浏览器配置 ==========
    HEADLESS = False
    BROWSER_TIMEOUT = 30000
    VIEWPORT_WIDTH = 1400
    VIEWPORT_HEIGHT = 1000
    
    # ============================================================
    # 🔑 步骤开关（每个步骤独立控制）
    # ============================================================
    
    # 第一步：扫描所有产品（获取图片、名称、Sharebar）
    # True=执行扫描, False=跳过
    ENABLE_SCAN = False
    
    # 第二步：二次确认（对无Sharebar的产品重新检查）
    # True=执行二次确认, False=跳过
    ENABLE_VERIFY = False
    
    # 第三步：生成二维码并合并图片
    # True=生成二维码, False=跳过
    ENABLE_QR = False
    
    # 第四步：导出文档（HTML/PDF/Word）
    # True=导出文档, False=跳过
    ENABLE_EXPORT = True
    
    # ============================================================
    # 运行模式
    # ============================================================
    # "full" | "scan" | "export" | "fetch"
    RUN_MODE = "full"
    
    # ============================================================
    # 二次确认配置
    # ============================================================
    # 是否启用二次确认（对无Sharebar的产品重新检查）
    ENABLE_RETRY = False
    
    # 二次确认重试次数（0=不重试，1=尝试1次，3=尝试3次）
    RETRY_COUNT = 1
    
    # ============================================================
    # Sharebar 获取配置
    # ============================================================
    SHAREBAR_RETRY_COUNT = 1
    
    # ============================================================
    # 导出开关
    # ============================================================
    ENABLE_SHAREBAR = True
    ENABLE_QRCODE = True
    ENABLE_WORD = True
    ENABLE_HTML = True
    
    # ============================================================
    # 处理配置
    # ============================================================
    PRODUCTS_PER_BATCH = 10
    REQUEST_DELAY = 1.5
    
    @classmethod
    def ensure_directories(cls):
        """确保所有目录存在"""
        dirs = [
            cls.PRODUCTS_DIR,
            cls.EXPORTS_DIR,
            cls.LOGS_DIR,
        ]
        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
        return cls
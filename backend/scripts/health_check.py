import time
import logging

# 配置日志输出到标准输出（必须配置才能显示）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

def main():
    logger.info("脚本启动...")
    
    logger.info("模拟检测")
    time.sleep(5)
    logger.info("检测成功")


if __name__ == '__main__':
    main()

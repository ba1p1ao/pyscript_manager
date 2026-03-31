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
    
    count = 0
    while True:
        count += 1
        logger.info(f"正在运行... 第 {count} 次")
        time.sleep(10)


if __name__ == '__main__':
    main()

"""
YAML 配置文件管理模块
负责读取、解析、验证和保存脚本配置
"""
import yaml
import os
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from app.database import get_db_context
from app.models import ScriptConfig

@dataclass
class ScriptConfigData:
    """脚本配置数据类"""
    name: str
    script_path: str
    description: str = ""
    schedule: Optional[str] = None
    schedule_type: str = "manual"  # manual, cron, interval
    interval_seconds: Optional[int] = None
    max_retries: int = 3
    retry_delay: int = 60
    timeout: int = 3600
    working_dir: Optional[str] = None
    env_vars: Optional[Dict[str, str]] = None
    python_path: Optional[str] = None
    enabled: bool = True
    auto_start: bool = False

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        # 过滤 None 值
        return {k: v for k, v in data.items() if v is not None}


class ConfigManager:
    """配置文件管理器"""

    def __init__(self, config_file: str = None):
        if config_file is None:
            config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config')
            os.makedirs(config_dir, exist_ok=True)
            config_file = os.path.join(config_dir, 'scripts.yaml')
        
        self.config_file = config_file
        self.configs: Dict[str, ScriptConfigData] = {}
        self._load_config()

    def _load_config(self):
        """加载配置文件"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}
                
                scripts = data.get('scripts', [])
                for item in scripts:
                    config = ScriptConfigData(
                        name=item.get('name'),
                        script_path=item.get('script_path'),
                        description=item.get('description', ''),
                        schedule=item.get('schedule'),
                        schedule_type=item.get('schedule_type', 'manual'),
                        interval_seconds=item.get('interval_seconds'),
                        max_retries=item.get('max_retries', 3),
                        retry_delay=item.get('retry_delay', 60),
                        timeout=item.get('timeout', 3600),
                        working_dir=item.get('working_dir'),
                        env_vars=item.get('env_vars'),
                        python_path=item.get('python_path'),
                        enabled=item.get('enabled', True),
                        auto_start=item.get('auto_start', False),
                    )
                    self.configs[config.name] = config
                
                print(f"已加载 {len(self.configs)} 个脚本配置")
            except Exception as e:
                print(f"加载配置文件失败: {e}")
                self._create_default_config()
        else:
            self._create_default_config()

    def _create_default_config(self):
        """创建默认配置文件"""
        default_config = {
            'scripts': [
                {
                    'name': 'example_script',
                    'script_path': '/path/to/your/script.py',
                    'description': '示例脚本配置',
                    'schedule_type': 'manual',
                    'max_retries': 3,
                    'retry_delay': 60,
                    'timeout': 3600,
                    'enabled': True,
                    'auto_start': False,
                }
            ]
        }
        
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        with open(self.config_file, 'w', encoding='utf-8') as f:
            yaml.dump(default_config, f, allow_unicode=True, default_flow_style=False)
        
        print(f"已创建默认配置文件: {self.config_file}")

    def save_config(self):
        """保存配置到文件"""
        data = {
            'scripts': [config.to_dict() for config in self.configs.values()]
        }
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
        
        print(f"配置已保存: {self.config_file}")

    def get_all_configs(self) -> Dict[str, ScriptConfigData]:
        """获取所有配置"""
        return self.configs

    def get_config(self, name: str) -> Optional[ScriptConfigData]:
        """获取指定名称的配置"""
        return self.configs.get(name)

    def add_config(self, config: ScriptConfigData) -> bool:
        """添加脚本配置"""
        if config.name in self.configs:
            return False
        
        # 验证脚本路径
        if not os.path.isabs(config.script_path):
            return False
        
        self.configs[config.name] = config
        self.save_config()
        return True

    def update_config(self, name: str, **kwargs) -> bool:
        """更新脚本配置"""
        if name not in self.configs:
            return False
        
        config = self.configs[name]
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        self.save_config()
        return True

    def remove_config(self, name: str) -> bool:
        """删除脚本配置"""
        if name not in self.configs:
            return False
        
        del self.configs[name]
        self.save_config()
        return True

    def reload_config(self):
        """重新加载配置文件"""
        self.configs.clear()
        self._load_config()

    def validate_config(self, config: ScriptConfigData) -> List[str]:
        """验证配置，返回错误列表"""
        errors = []
        
        if not config.name:
            errors.append("脚本名称不能为空")
        
        if not config.script_path:
            errors.append("脚本路径不能为空")
        elif not os.path.isabs(config.script_path):
            errors.append("脚本路径必须是绝对路径")
        
        if config.schedule_type not in ['manual', 'cron', 'interval']:
            errors.append("调度类型必须是 manual、cron 或 interval")
        
        if config.schedule_type == 'interval' and not config.interval_seconds:
            errors.append("间隔调度必须指定间隔秒数")
        
        if config.max_retries < 0:
            errors.append("重试次数不能为负数")
        
        if config.timeout <= 0:
            errors.append("超时时间必须大于0")
        
        return errors

    def sync_config(self):
        """
        将 yaml 文件的配置信息同步到数据库中
        注意：不在此处处理调度任务，由 scheduler_service.start() 统一处理
        """
        self.reload_config()
    
        # 同步到数据库
        yaml_configs = self.configs

        with get_db_context() as db:
            # 获取数据库中的所有配置
            db_configs = db.query(ScriptConfig).all()
            db_names = {c.name: c for c in db_configs}
            
            for name, yaml_config in yaml_configs.items():
                # 添加新配置
                if not db_names.get(name):
                    new_config = ScriptConfig(
                        name=yaml_config.name,
                        script_path=yaml_config.script_path,
                        description=yaml_config.description,
                        schedule=yaml_config.schedule,
                        schedule_type=yaml_config.schedule_type,
                        interval_seconds=yaml_config.interval_seconds,
                        max_retries=yaml_config.max_retries,
                        retry_delay=yaml_config.retry_delay,
                        timeout=yaml_config.timeout,
                        working_dir=yaml_config.working_dir,
                        env_vars=str(yaml_config.env_vars) if yaml_config.env_vars else None,
                        python_path=yaml_config.python_path,
                        enabled=yaml_config.enabled,
                        auto_start=yaml_config.auto_start,
                        status='stopped'
                    )
                    db.add(new_config)
                else:
                    # 修改老配置
                    old_config = db_names[name]
                    for key, value in yaml_config.to_dict().items():
                        if key == "name":
                            continue
                        elif key == 'env_vars' and value:
                            setattr(old_config, key, str(value))
                        elif hasattr(old_config, key):
                            setattr(old_config, key, value)
                            
            # 删除数据库中有但是yaml文件中没有的配置            
            for db_config in db_configs:
                if not yaml_configs.get(db_config.name):
                    db.delete(db_config)
                    
            db.commit()
            
        return yaml_configs
    
# 全局配置管理器实例
config_manager = ConfigManager()

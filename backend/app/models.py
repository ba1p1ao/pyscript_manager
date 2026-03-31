from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Index
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class ScriptConfig(Base):
    """
    脚本配置表 - 与 YAML 配置文件同步
    """
    __tablename__ = 'script_config'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True, comment='脚本名称（唯一标识）')
    script_path = Column(String(512), nullable=False, comment='脚本绝对路径')
    description = Column(Text, nullable=True, comment='脚本描述')
    
    # 运行配置
    schedule = Column(String(128), nullable=True, comment='运行时间（cron表达式或时间间隔）')
    schedule_type = Column(String(32), default='manual', comment='调度类型: manual/cron/interval')
    interval_seconds = Column(Integer, nullable=True, comment='间隔运行秒数')
    max_retries = Column(Integer, default=3, comment='最大重试次数')
    retry_delay = Column(Integer, default=60, comment='重试间隔（秒）')
    timeout = Column(Integer, default=3600, comment='超时时间（秒）')
    
    # 运行环境
    working_dir = Column(String(512), nullable=True, comment='工作目录')
    env_vars = Column(Text, nullable=True, comment='环境变量（JSON格式）')
    python_path = Column(String(512), nullable=True, comment='Python解释器路径')
    
    # 状态
    enabled = Column(Boolean, default=True, comment='是否启用')
    auto_start = Column(Boolean, default=False, comment='是否自动启动')
    current_pid = Column(Integer, nullable=True, comment='当前运行的进程ID')
    status = Column(String(32), default='stopped', comment='状态: stopped/running/pending/error')
    last_run_time = Column(DateTime, nullable=True, comment='最后运行时间')
    next_run_time = Column(DateTime, nullable=True, comment='下次运行时间')
    
    # 元数据
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('idx_script_name', 'name'),
        Index('idx_script_status', 'status'),
    )

    def __repr__(self):
        return f"<ScriptConfig(id={self.id}, name={self.name}, status={self.status})>"


class ScriptHistory(Base):
    """
    脚本运行历史记录表
    """
    __tablename__ = 'script_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    script_name = Column(String(255), nullable=False, index=True, comment='脚本名称')
    script_path = Column(String(512), nullable=False, comment='脚本路径')
    pid = Column(Integer, nullable=True, comment='进程ID')
    
    # 时间信息
    start_time = Column(DateTime, default=datetime.now, nullable=False, comment='开始时间')
    end_time = Column(DateTime, nullable=True, comment='结束时间')
    duration = Column(Integer, nullable=True, comment='运行时长（秒）')
    
    # 运行结果
    exit_code = Column(Integer, nullable=True, comment='退出码')
    status = Column(String(32), nullable=False, default='running', comment='运行状态: running/completed/failed/stopped/timeout')
    retry_count = Column(Integer, default=0, comment='当前重试次数')
    
    # 日志
    log_file = Column(String(512), nullable=True, comment='日志文件路径')
    error_message = Column(Text, nullable=True, comment='错误信息')

    # 复合索引用于优化查询
    __table_args__ = (
        Index('idx_history_script_status', 'script_name', 'status'),
        Index('idx_history_start_time', 'start_time'),
    )

    def __repr__(self):
        return f"<ScriptHistory(id={self.id}, script_name={self.script_name}, status={self.status})>"


class SystemLog(Base):
    """
    系统操作日志表
    """
    __tablename__ = 'system_log'

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.now, nullable=False, comment='时间戳')
    level = Column(String(16), nullable=False, comment='日志级别: INFO/WARNING/ERROR')
    module = Column(String(64), nullable=True, comment='模块名称')
    action = Column(String(64), nullable=False, comment='操作类型')
    target = Column(String(255), nullable=True, comment='操作目标')
    message = Column(Text, nullable=True, comment='详细信息')
    user_ip = Column(String(64), nullable=True, comment='操作IP')

    __table_args__ = (
        Index('idx_log_timestamp', 'timestamp'),
        Index('idx_log_level', 'level'),
    )

    def __repr__(self):
        return f"<SystemLog(id={self.id}, action={self.action}, target={self.target})>"

"""
日志清理服务
提供日志文件的自动清理、归档和数据库记录清理功能
"""
import os
import tarfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple
import asyncio

from app.logger import LogConfig, get_logger
from app.database import get_db_context
from app.models import ScriptHistory, SystemLog


class LogCleaner:
    """日志清理服务"""
    
    def __init__(self):
        self.logger = get_logger('log_cleaner')
        LogConfig.ensure_dirs()
    
    def get_log_stats(self) -> Dict:
        """获取日志统计信息"""
        stats = {
            'app_logs': self._get_dir_stats(LogConfig.APP_LOG_DIR),
            'script_logs': self._get_dir_stats(LogConfig.SCRIPT_LOG_DIR),
            'archive_logs': self._get_dir_stats(LogConfig.ARCHIVE_DIR),
            'total_size_mb': 0,
            'script_count': 0,
            'oldest_log_date': None,
        }
        
        # 计算总大小
        stats['total_size_mb'] = (
            stats['app_logs']['size_mb'] + 
            stats['script_logs']['size_mb'] + 
            stats['archive_logs']['size_mb']
        )
        
        # 统计脚本数量
        if LogConfig.SCRIPT_LOG_DIR.exists():
            stats['script_count'] = len([
                d for d in LogConfig.SCRIPT_LOG_DIR.iterdir() 
                if d.is_dir()
            ])
        
        # 找最旧的日志文件
        oldest = self._find_oldest_log_file()
        if oldest:
            stats['oldest_log_date'] = datetime.fromtimestamp(
                oldest.stat().st_mtime
            ).strftime('%Y-%m-%d')
        
        # 数据库统计
        with get_db_context() as db:
            stats['db_history_count'] = db.query(ScriptHistory).count()
            stats['db_system_log_count'] = db.query(SystemLog).count()
        
        return stats
    
    def _get_dir_stats(self, dir_path: Path) -> Dict:
        """获取目录统计信息"""
        if not dir_path.exists():
            return {'file_count': 0, 'size_mb': 0}
        
        total_size = 0
        file_count = 0
        
        for root, dirs, files in os.walk(dir_path):
            for file in files:
                file_path = Path(root) / file
                try:
                    total_size += file_path.stat().st_size
                    file_count += 1
                except:
                    pass
        
        return {
            'file_count': file_count,
            'size_mb': round(total_size / (1024 * 1024), 2)
        }
    
    def _find_oldest_log_file(self) -> Path:
        """找到最旧的日志文件"""
        oldest = None
        oldest_time = float('inf')
        
        for log_dir in [LogConfig.APP_LOG_DIR, LogConfig.SCRIPT_LOG_DIR]:
            if not log_dir.exists():
                continue
            
            for root, dirs, files in os.walk(log_dir):
                for file in files:
                    if file.endswith('.log'):
                        file_path = Path(root) / file
                        try:
                            mtime = file_path.stat().st_mtime
                            if mtime < oldest_time:
                                oldest_time = mtime
                                oldest = file_path
                        except:
                            pass
        
        return oldest
    
    def clean_script_logs(self, days: int = None) -> Tuple[int, int]:
        """
        清理过期的脚本日志文件
        
        :param days: 保留天数，默认使用配置值
        :return: (删除文件数, 释放空间 MB)
        """
        retention_days = days or LogConfig.SCRIPT_RETENTION_DAYS
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        deleted_count = 0
        freed_space = 0
        
        if not LogConfig.SCRIPT_LOG_DIR.exists():
            return deleted_count, freed_space
        
        for script_dir in LogConfig.SCRIPT_LOG_DIR.iterdir():
            if not script_dir.is_dir():
                continue
            
            # 清理过期日志文件
            for log_file in script_dir.glob("*.log"):
                try:
                    mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                    if mtime < cutoff_date:
                        file_size = log_file.stat().st_size
                        log_file.unlink()
                        deleted_count += 1
                        freed_space += file_size
                        self.logger.debug(f"删除过期日志: {log_file}")
                except Exception as e:
                    self.logger.error(f"删除日志文件失败 {log_file}: {e}")
            
            # 限制每个脚本的日志文件数量
            log_files = sorted(
                script_dir.glob("*.log"),
                key=lambda f: f.stat().st_mtime,
                reverse=True
            )
            
            if len(log_files) > LogConfig.SCRIPT_MAX_FILES_PER_SCRIPT:
                for old_file in log_files[LogConfig.SCRIPT_MAX_FILES_PER_SCRIPT:]:
                    try:
                        file_size = old_file.stat().st_size
                        old_file.unlink()
                        deleted_count += 1
                        freed_space += file_size
                        self.logger.debug(f"删除多余日志: {old_file}")
                    except Exception as e:
                        self.logger.error(f"删除日志文件失败 {old_file}: {e}")
        
        freed_mb = round(freed_space / (1024 * 1024), 2)
        self.logger.info(f"清理脚本日志完成: 删除 {deleted_count} 个文件, 释放 {freed_mb} MB")
        return deleted_count, freed_mb
    
    def archive_old_logs(self, days: int = None) -> int:
        """
        归档旧日志（压缩）
        
        :param days: 超过此天数的日志将被归档
        :return: 归档文件数
        """
        archive_days = days or LogConfig.ARCHIVE_AFTER_DAYS
        cutoff_date = datetime.now() - timedelta(days=archive_days)
        
        archived_count = 0
        
        if not LogConfig.SCRIPT_LOG_DIR.exists():
            return archived_count
        
        # 按月归档
        for script_dir in LogConfig.SCRIPT_LOG_DIR.iterdir():
            if not script_dir.is_dir():
                continue
            
            # 找到需要归档的日志文件
            old_logs = []
            for log_file in script_dir.glob("*.log"):
                try:
                    mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                    if mtime < cutoff_date:
                        old_logs.append((log_file, mtime))
                except:
                    pass
            
            if not old_logs:
                continue
            
            # 创建归档文件
            archive_name = f"{script_dir.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tar.gz"
            archive_path = LogConfig.ARCHIVE_DIR / archive_name
            
            try:
                with tarfile.open(archive_path, 'w:gz') as tar:
                    for log_file, _ in old_logs:
                        tar.add(log_file, arcname=log_file.name)
                        log_file.unlink()
                        archived_count += 1
                
                self.logger.info(f"归档日志: {archive_path}")
            except Exception as e:
                self.logger.error(f"归档失败 {script_dir.name}: {e}")
        
        return archived_count
    
    def clean_old_archives(self, days: int = None) -> int:
        """
        清理过期的归档文件
        
        :param days: 归档文件保留天数
        :return: 删除的归档文件数
        """
        retention_days = days or LogConfig.ARCHIVE_RETENTION_DAYS
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        deleted_count = 0
        
        if not LogConfig.ARCHIVE_DIR.exists():
            return deleted_count
        
        for archive_file in LogConfig.ARCHIVE_DIR.glob("*.tar.gz"):
            try:
                mtime = datetime.fromtimestamp(archive_file.stat().st_mtime)
                if mtime < cutoff_date:
                    archive_file.unlink()
                    deleted_count += 1
                    self.logger.debug(f"删除过期归档: {archive_file}")
            except Exception as e:
                self.logger.error(f"删除归档文件失败 {archive_file}: {e}")
        
        self.logger.info(f"清理归档文件完成: 删除 {deleted_count} 个")
        return deleted_count
    
    def clean_database_history(self, keep_count: int = None) -> int:
        """
        清理数据库中的脚本运行历史
        
        :param keep_count: 每个脚本保留的记录数
        :return: 删除的记录数
        """
        retention_count = keep_count or LogConfig.HISTORY_RETENTION_COUNT
        deleted_count = 0
        
        with get_db_context() as db:
            # 获取所有脚本名称
            script_names = db.query(ScriptHistory.script_name).distinct().all()
            
            for (script_name,) in script_names:
                # 获取该脚本的记录总数
                total = db.query(ScriptHistory).filter(
                    ScriptHistory.script_name == script_name
                ).count()
                
                if total <= retention_count:
                    continue
                
                # 找到需要保留的最小 ID
                keep_ids = db.query(ScriptHistory.id).filter(
                    ScriptHistory.script_name == script_name
                ).order_by(ScriptHistory.start_time.desc()).limit(retention_count).all()
                
                keep_id_list = [id for (id,) in keep_ids]
                min_keep_id = min(keep_id_list)
                
                # 删除旧记录
                deleted = db.query(ScriptHistory).filter(
                    ScriptHistory.script_name == script_name,
                    ScriptHistory.id < min_keep_id
                ).delete(synchronize_session=False)
                
                deleted_count += deleted
            
            db.commit()
        
        self.logger.info(f"清理历史记录完成: 删除 {deleted_count} 条记录")
        return deleted_count
    
    def clean_system_logs(self, days: int = None) -> int:
        """
        清理数据库中的系统日志
        
        :param days: 保留天数
        :return: 删除的记录数
        """
        retention_days = days or LogConfig.SYSTEM_LOG_RETENTION_DAYS
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        with get_db_context() as db:
            deleted = db.query(SystemLog).filter(
                SystemLog.timestamp < cutoff_date
            ).delete(synchronize_session=False)
            db.commit()
        
        self.logger.info(f"清理系统日志完成: 删除 {deleted} 条记录")
        return deleted
    
    def run_full_cleanup(self) -> Dict:
        """
        执行完整清理
        
        :return: 清理结果统计
        """
        self.logger.info("开始执行日志清理任务...")
        
        results = {
            'script_logs_deleted': 0,
            'script_logs_freed_mb': 0,
            'archives_created': 0,
            'archives_deleted': 0,
            'history_deleted': 0,
            'system_logs_deleted': 0,
            'start_time': datetime.now().isoformat(),
            'end_time': None,
        }
        
        try:
            # 1. 归档旧日志
            results['archives_created'] = self.archive_old_logs()
            
            # 2. 清理过期日志
            deleted, freed = self.clean_script_logs()
            results['script_logs_deleted'] = deleted
            results['script_logs_freed_mb'] = freed
            
            # 3. 清理过期归档
            results['archives_deleted'] = self.clean_old_archives()
            
            # 4. 清理数据库历史
            results['history_deleted'] = self.clean_database_history()
            
            # 5. 清理系统日志
            results['system_logs_deleted'] = self.clean_system_logs()
            
        except Exception as e:
            self.logger.error(f"清理任务执行失败: {e}")
            results['error'] = str(e)
        
        results['end_time'] = datetime.now().isoformat()
        self.logger.info(f"日志清理任务完成: {results}")
        
        return results


# 全局清理器实例
log_cleaner = LogCleaner()


def schedule_log_cleanup(scheduler_service):
    """
    注册日志清理定时任务到调度器
    每天凌晨 3 点执行
    """
    from apscheduler.triggers.cron import CronTrigger
    
    async def cleanup_job():
        """清理任务"""
        log_cleaner.run_full_cleanup()
    
    scheduler_service.scheduler.add_job(
        func=cleanup_job,
        trigger=CronTrigger(hour=3, minute=0),
        id='log_cleanup',
        name='日志清理任务',
        replace_existing=True
    )
    
    get_logger('log_cleaner').info("日志清理定时任务已注册 (每天 03:00)")

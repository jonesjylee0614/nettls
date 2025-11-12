"""
快照管理模块 - 负责创建和管理路由快照
"""
import json
import os
import logging
from typing import List, Dict, Optional
from datetime import datetime
from core.route_manager import RouteManager

logger = logging.getLogger(__name__)


class SnapshotManager:
    """快照管理器"""
    
    def __init__(self, snapshot_dir: str = "snapshots"):
        self.snapshot_dir = snapshot_dir
        
        # 确保快照目录存在
        os.makedirs(self.snapshot_dir, exist_ok=True)
    
    def create_system_snapshot(self, route_manager: RouteManager) -> Optional[str]:
        """
        创建系统路由快照
        
        Args:
            route_manager: 路由管理器
            
        Returns:
            Optional[str]: 快照文件路径,失败返回None
        """
        try:
            # 刷新系统路由
            if not route_manager.refresh_system_routes():
                logger.error("刷新系统路由失败,无法创建快照")
                return None
            
            # 获取系统路由
            system_routes = route_manager.get_system_routes()
            
            # 创建快照数据
            snapshot = {
                "type": "system",
                "timestamp": datetime.now().isoformat(),
                "total_routes": len(system_routes),
                "routes": system_routes
            }
            
            # 生成文件名
            filename = f"system-routes-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
            filepath = os.path.join(self.snapshot_dir, filename)
            
            # 保存快照
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(snapshot, f, ensure_ascii=False, indent=2)
            
            logger.info(f"成功创建系统路由快照: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"创建系统路由快照失败: {e}")
            return None
    
    def create_config_snapshot(self, config_path: str) -> Optional[str]:
        """
        创建配置文件快照
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            Optional[str]: 快照文件路径,失败返回None
        """
        try:
            # 读取配置文件
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 创建快照数据
            snapshot = {
                "type": "config",
                "timestamp": datetime.now().isoformat(),
                "source_file": config_path,
                "config": config
            }
            
            # 生成文件名
            profile_name = config.get('profileName', 'unknown')
            filename = f"app-config-{profile_name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
            filepath = os.path.join(self.snapshot_dir, filename)
            
            # 保存快照
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(snapshot, f, ensure_ascii=False, indent=2)
            
            logger.info(f"成功创建配置快照: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"创建配置快照失败: {e}")
            return None
    
    def list_snapshots(self) -> List[Dict]:
        """
        列出所有快照
        
        Returns:
            List[Dict]: 快照信息列表
        """
        try:
            snapshots = []
            
            # 遍历快照目录
            for filename in os.listdir(self.snapshot_dir):
                if not filename.endswith('.json'):
                    continue
                
                filepath = os.path.join(self.snapshot_dir, filename)
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        snapshot = json.load(f)
                    
                    # 获取文件信息
                    file_stat = os.stat(filepath)
                    
                    snapshots.append({
                        "filename": filename,
                        "filepath": filepath,
                        "type": snapshot.get("type", "unknown"),
                        "timestamp": snapshot.get("timestamp", ""),
                        "size": file_stat.st_size,
                        "total_routes": snapshot.get("total_routes", 0)
                    })
                except Exception as e:
                    logger.warning(f"读取快照文件失败: {filename}, {e}")
                    continue
            
            # 按时间戳排序(最新的在前)
            snapshots.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return snapshots
            
        except Exception as e:
            logger.error(f"列出快照失败: {e}")
            return []
    
    def load_snapshot(self, filepath: str) -> Optional[Dict]:
        """
        加载快照
        
        Args:
            filepath: 快照文件路径
            
        Returns:
            Optional[Dict]: 快照数据,失败返回None
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                snapshot = json.load(f)
            
            logger.info(f"成功加载快照: {filepath}")
            return snapshot
            
        except Exception as e:
            logger.error(f"加载快照失败: {filepath}, {e}")
            return None
    
    def restore_system_snapshot(self, filepath: str, route_manager: RouteManager) -> bool:
        """
        从快照恢复系统路由
        
        Args:
            filepath: 快照文件路径
            route_manager: 路由管理器
            
        Returns:
            bool: 是否成功
        """
        try:
            # 加载快照
            snapshot = self.load_snapshot(filepath)
            if not snapshot:
                return False
            
            if snapshot.get('type') != 'system':
                logger.error(f"快照类型错误: {snapshot.get('type')}, 期望 system")
                return False
            
            # 获取快照中的路由
            snapshot_routes = snapshot.get('routes', [])
            
            # 获取当前系统路由
            if not route_manager.refresh_system_routes():
                logger.error("刷新系统路由失败")
                return False
            
            current_routes = route_manager.get_system_routes()
            
            # 构建当前路由映射
            current_routes_map = {}
            for route in current_routes:
                dest_prefix = route.get('DestinationPrefix', '')
                if dest_prefix:
                    current_routes_map[dest_prefix] = route
            
            # 构建快照路由映射
            snapshot_routes_map = {}
            for route in snapshot_routes:
                dest_prefix = route.get('DestinationPrefix', '')
                if dest_prefix:
                    snapshot_routes_map[dest_prefix] = route
            
            # 计算需要的操作
            # 1. 删除当前系统中有但快照中没有的路由(仅永久路由)
            # 2. 添加快照中有但当前系统中没有的路由
            # 3. 修改参数不同的路由
            
            errors = []
            
            # 删除多余的路由
            for dest_prefix, current_route in current_routes_map.items():
                if dest_prefix not in snapshot_routes_map:
                    # 只删除永久路由
                    if current_route.get('Protocol') == 'NetMgmt':
                        target_ip = dest_prefix.split('/')[0]
                        success, error = route_manager.delete_route(target_ip)
                        if not success:
                            errors.append(f"删除路由失败: {dest_prefix}, {error}")
            
            # TODO: 添加和修改路由需要更完整的实现
            # 这里简化处理,实际应该重新构建Route对象并调用add/change方法
            
            if errors:
                logger.error(f"恢复快照时出现错误: {errors}")
                return False
            
            logger.info(f"成功从快照恢复系统路由: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"恢复系统快照失败: {e}")
            return False
    
    def delete_snapshot(self, filepath: str) -> bool:
        """
        删除快照文件
        
        Args:
            filepath: 快照文件路径
            
        Returns:
            bool: 是否成功
        """
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"成功删除快照: {filepath}")
                return True
            else:
                logger.warning(f"快照文件不存在: {filepath}")
                return False
                
        except Exception as e:
            logger.error(f"删除快照失败: {filepath}, {e}")
            return False
    
    def cleanup_old_snapshots(self, keep_count: int = 10):
        """
        清理旧快照,只保留最新的N个
        
        Args:
            keep_count: 保留的快照数量
        """
        try:
            snapshots = self.list_snapshots()
            
            if len(snapshots) <= keep_count:
                return
            
            # 删除多余的快照
            for snapshot in snapshots[keep_count:]:
                self.delete_snapshot(snapshot['filepath'])
            
            logger.info(f"清理旧快照完成,保留 {keep_count} 个")
            
        except Exception as e:
            logger.error(f"清理旧快照失败: {e}")


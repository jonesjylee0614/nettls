"""
配置管理模块 - 负责读取和保存 Profile 配置
"""
import json
import os
import logging
from typing import List, Dict, Optional
from datetime import datetime
from core.route_manager import Route

logger = logging.getLogger(__name__)


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, profiles_dir: str = "profiles"):
        self.profiles_dir = profiles_dir
        self.current_profile: str = "home"
        self.config: Dict = {}
        
        # 确保配置目录存在
        os.makedirs(self.profiles_dir, exist_ok=True)
    
    def get_profile_path(self, profile_name: str) -> str:
        """
        获取配置文件完整路径
        
        Args:
            profile_name: Profile 名称(不含扩展名)
            
        Returns:
            str: 完整路径
        """
        if not profile_name.endswith('.json'):
            profile_name = f"{profile_name}.json"
        return os.path.join(self.profiles_dir, profile_name)
    
    def load_profile(self, profile_name: str) -> bool:
        """
        加载 Profile 配置
        
        Args:
            profile_name: Profile 名称
            
        Returns:
            bool: 是否成功
        """
        try:
            profile_path = self.get_profile_path(profile_name)
            
            # 如果文件不存在,创建默认配置
            if not os.path.exists(profile_path):
                logger.warning(f"Profile 不存在,创建默认配置: {profile_name}")
                self.create_default_profile(profile_name)
            
            with open(profile_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            
            self.current_profile = profile_name.replace('.json', '')
            logger.info(f"成功加载 Profile: {profile_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"加载 Profile 失败: {e}")
            return False
    
    def save_profile(self, profile_name: Optional[str] = None) -> bool:
        """
        保存 Profile 配置
        
        Args:
            profile_name: Profile 名称(None 表示保存到当前 Profile)
            
        Returns:
            bool: 是否成功
        """
        try:
            if profile_name is None:
                profile_name = self.current_profile
            
            profile_path = self.get_profile_path(profile_name)
            
            # 更新时间戳
            self.config['lastModified'] = datetime.now().isoformat()
            
            with open(profile_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            
            logger.info(f"成功保存 Profile: {profile_name}")
            return True
            
        except Exception as e:
            logger.error(f"保存 Profile 失败: {e}")
            return False
    
    def create_default_profile(self, profile_name: str) -> bool:
        """
        创建默认 Profile 配置
        
        Args:
            profile_name: Profile 名称
            
        Returns:
            bool: 是否成功
        """
        try:
            self.config = {
                "version": 1,
                "profileName": profile_name.replace('.json', ''),
                "created": datetime.now().isoformat(),
                "lastModified": datetime.now().isoformat(),
                "defaults": {
                    "metric": 5,
                    "persistent": True,
                    "verify": {
                        "routeHit": True,
                        "trace": False,
                        "timeoutMs": 1500
                    }
                },
                "interfacePolicy": {
                    "physical": {
                        "nameMatch": "",
                        "gateway": "",
                        "mac": ""
                    },
                    "wireguard": {
                        "nameMatch": "client",
                        "fullTunnelGuard": True
                    }
                },
                "routes": [],
                "pinned": {}
            }
            
            return self.save_profile(profile_name)
            
        except Exception as e:
            logger.error(f"创建默认配置失败: {e}")
            return False
    
    def get_routes(self) -> List[Route]:
        """
        获取配置中的路由列表
        
        Returns:
            List[Route]: 路由列表
        """
        routes = []
        routes_data = self.config.get('routes', [])
        
        for route_data in routes_data:
            route = Route.from_dict(route_data)
            routes.append(route)
        
        return routes
    
    def set_routes(self, routes: List[Route]):
        """
        更新配置中的路由列表
        
        Args:
            routes: 路由列表
        """
        self.config['routes'] = [route.to_dict() for route in routes]
    
    def add_route(self, route: Route):
        """
        添加路由到配置
        
        Args:
            route: 路由对象
        """
        if 'routes' not in self.config:
            self.config['routes'] = []
        
        self.config['routes'].append(route.to_dict())
    
    def remove_route(self, index: int):
        """
        从配置中删除路由
        
        Args:
            index: 路由索引
        """
        if 'routes' in self.config and 0 <= index < len(self.config['routes']):
            del self.config['routes'][index]
    
    def get_default_metric(self) -> int:
        """获取默认 Metric 值"""
        return self.config.get('defaults', {}).get('metric', 5)
    
    def get_default_interface(self) -> str:
        """获取默认物理接口名称"""
        return self.config.get('interfacePolicy', {}).get('physical', {}).get('nameMatch', '')
    
    def set_default_interface(self, interface_name: str, gateway: str = "", mac: str = ""):
        """
        设置默认物理接口
        
        Args:
            interface_name: 接口名称
            gateway: 默认网关
            mac: MAC 地址
        """
        if 'interfacePolicy' not in self.config:
            self.config['interfacePolicy'] = {}
        
        if 'physical' not in self.config['interfacePolicy']:
            self.config['interfacePolicy']['physical'] = {}
        
        self.config['interfacePolicy']['physical']['nameMatch'] = interface_name
        self.config['interfacePolicy']['physical']['gateway'] = gateway
        self.config['interfacePolicy']['physical']['mac'] = mac
    
    def list_profiles(self) -> List[str]:
        """
        列出所有 Profile
        
        Returns:
            List[str]: Profile 名称列表
        """
        try:
            files = os.listdir(self.profiles_dir)
            profiles = [f.replace('.json', '') for f in files if f.endswith('.json')]
            return sorted(profiles)
        except Exception as e:
            logger.error(f"列出 Profile 失败: {e}")
            return []
    
    def delete_profile(self, profile_name: str) -> bool:
        """
        删除 Profile
        
        Args:
            profile_name: Profile 名称
            
        Returns:
            bool: 是否成功
        """
        try:
            profile_path = self.get_profile_path(profile_name)
            
            if os.path.exists(profile_path):
                os.remove(profile_path)
                logger.info(f"成功删除 Profile: {profile_name}")
                return True
            else:
                logger.warning(f"Profile 不存在: {profile_name}")
                return False
                
        except Exception as e:
            logger.error(f"删除 Profile 失败: {e}")
            return False
    
    def export_profile(self, profile_name: str, export_path: str) -> bool:
        """
        导出 Profile 到指定路径
        
        Args:
            profile_name: Profile 名称
            export_path: 导出路径
            
        Returns:
            bool: 是否成功
        """
        try:
            profile_path = self.get_profile_path(profile_name)
            
            if not os.path.exists(profile_path):
                logger.error(f"Profile 不存在: {profile_name}")
                return False
            
            with open(profile_path, 'r', encoding='utf-8') as src:
                config = json.load(src)
            
            with open(export_path, 'w', encoding='utf-8') as dst:
                json.dump(config, dst, ensure_ascii=False, indent=2)
            
            logger.info(f"成功导出 Profile: {profile_name} -> {export_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出 Profile 失败: {e}")
            return False
    
    def import_profile(self, import_path: str, profile_name: str) -> bool:
        """
        从文件导入 Profile
        
        Args:
            import_path: 导入文件路径
            profile_name: 目标 Profile 名称
            
        Returns:
            bool: 是否成功
        """
        try:
            with open(import_path, 'r', encoding='utf-8') as src:
                config = json.load(src)
            
            # 更新 Profile 名称
            config['profileName'] = profile_name.replace('.json', '')
            config['lastModified'] = datetime.now().isoformat()
            
            profile_path = self.get_profile_path(profile_name)
            
            with open(profile_path, 'w', encoding='utf-8') as dst:
                json.dump(config, dst, ensure_ascii=False, indent=2)
            
            logger.info(f"成功导入 Profile: {import_path} -> {profile_name}")
            return True
            
        except Exception as e:
            logger.error(f"导入 Profile 失败: {e}")
            return False


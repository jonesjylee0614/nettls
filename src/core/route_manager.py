"""
路由管理模块 - 负责读取、应用、验证路由
"""
import logging
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from utils.powershell import run_powershell_json, run_route_cmd

logger = logging.getLogger(__name__)


@dataclass
class Route:
    """路由信息"""
    enabled: bool = True
    target: str = ""  # 目标 IP/CIDR 或域名
    prefix_length: int = 32  # CIDR 前缀长度
    gateway: str = ""  # 网关
    interface_name: str = ""  # 接口名称
    metric: int = 5  # 跃点数
    persistent: bool = True  # 是否持久
    pin: bool = False  # 是否固定解析(域名)
    group: str = ""  # 分组
    desc: str = ""  # 描述
    
    # 运行时字段
    if_index: int = 0  # 接口索引(运行时解析)
    last_apply_result: str = ""  # 最后应用结果
    last_apply_time: str = ""  # 最后应用时间
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Route':
        """从字典创建"""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})
    
    def get_destination_prefix(self) -> str:
        """获取目标前缀(IP/CIDR 格式)"""
        if '/' in self.target:
            return self.target
        return f"{self.target}/{self.prefix_length}"
    
    def get_subnet_mask(self) -> str:
        """获取子网掩码"""
        return RouteManager.prefix_to_mask(self.prefix_length)


class RouteManager:
    """路由管理器"""
    
    def __init__(self):
        self.routes: List[Route] = []
        self._system_routes: List[dict] = []
    
    def refresh_system_routes(self) -> bool:
        """
        刷新系统路由表(仅 IPv4)
        
        Returns:
            bool: 是否成功
        """
        try:
            command = (
                "Get-NetRoute -AddressFamily IPv4 | "
                "Select-Object DestinationPrefix, NextHop, ifIndex, RouteMetric, Protocol | "
                "ConvertTo-Json"
            )
            
            success, data, error = run_powershell_json(command)
            
            if not success:
                logger.error(f"获取系统路由失败: {error}")
                return False
            
            # 清空现有路由列表
            self._system_routes.clear()
            
            if data is None:
                logger.warning("系统路由表为空")
                return True
            
            # PowerShell 返回单个对象时不是数组
            if not isinstance(data, list):
                data = [data]
            
            self._system_routes = data
            logger.info(f"成功获取 {len(self._system_routes)} 条系统路由")
            
            return True
            
        except Exception as e:
            logger.error(f"刷新系统路由异常: {e}")
            return False
    
    def get_system_routes(self) -> List[dict]:
        """
        获取系统路由列表
        
        Returns:
            List[dict]: 系统路由列表
        """
        return self._system_routes.copy()
    
    def add_route(self, route: Route, if_index: int) -> Tuple[bool, str]:
        """
        添加路由到系统
        
        Args:
            route: 路由对象
            if_index: 接口索引
            
        Returns:
            Tuple[bool, str]: (是否成功, 错误信息)
        """
        try:
            # 构建 route 命令
            mask = route.get_subnet_mask()
            target_ip = route.target.split('/')[0] if '/' in route.target else route.target
            
            # route -p add <ip> mask <netmask> <gateway> IF <ifIndex> metric <metric>
            persistent_flag = "-p" if route.persistent else ""
            cmd = f"{persistent_flag} add {target_ip} mask {mask} {route.gateway} IF {if_index} metric {route.metric}"
            
            success, stdout, stderr = run_route_cmd(cmd)
            
            if not success:
                error_msg = stderr or stdout
                logger.error(f"添加路由失败: {error_msg}")
                return False, error_msg
            
            logger.info(f"成功添加路由: {target_ip}/{route.prefix_length}")
            return True, ""
            
        except Exception as e:
            logger.error(f"添加路由异常: {e}")
            return False, str(e)
    
    def change_route(self, route: Route, if_index: int) -> Tuple[bool, str]:
        """
        修改系统路由
        
        Args:
            route: 路由对象
            if_index: 接口索引
            
        Returns:
            Tuple[bool, str]: (是否成功, 错误信息)
        """
        try:
            mask = route.get_subnet_mask()
            target_ip = route.target.split('/')[0] if '/' in route.target else route.target
            
            # route change <ip> mask <netmask> <gateway> IF <ifIndex> metric <metric>
            cmd = f"change {target_ip} mask {mask} {route.gateway} IF {if_index} metric {route.metric}"
            
            success, stdout, stderr = run_route_cmd(cmd)
            
            if not success:
                error_msg = stderr or stdout
                logger.error(f"修改路由失败: {error_msg}")
                return False, error_msg
            
            logger.info(f"成功修改路由: {target_ip}/{route.prefix_length}")
            return True, ""
            
        except Exception as e:
            logger.error(f"修改路由异常: {e}")
            return False, str(e)
    
    def delete_route(self, target: str) -> Tuple[bool, str]:
        """
        删除系统路由
        
        Args:
            target: 目标 IP 或 CIDR
            
        Returns:
            Tuple[bool, str]: (是否成功, 错误信息)
        """
        try:
            target_ip = target.split('/')[0] if '/' in target else target
            
            # route delete <ip>
            cmd = f"delete {target_ip}"
            
            success, stdout, stderr = run_route_cmd(cmd)
            
            if not success:
                error_msg = stderr or stdout
                logger.error(f"删除路由失败: {error_msg}")
                return False, error_msg
            
            logger.info(f"成功删除路由: {target_ip}")
            return True, ""
            
        except Exception as e:
            logger.error(f"删除路由异常: {e}")
            return False, str(e)
    
    def verify_route(self, target: str) -> Tuple[bool, str]:
        """
        验证路由是否命中
        
        Args:
            target: 目标 IP
            
        Returns:
            Tuple[bool, str]: (是否命中, 输出信息)
        """
        try:
            target_ip = target.split('/')[0] if '/' in target else target
            
            # route print <ip>
            cmd = f"print {target_ip}"
            
            success, stdout, stderr = run_route_cmd(cmd)
            
            if not success:
                return False, stderr or stdout
            
            # 检查输出中是否包含目标 IP 的路由信息
            if target_ip in stdout:
                return True, stdout
            else:
                return False, "未找到匹配的路由"
            
        except Exception as e:
            logger.error(f"验证路由异常: {e}")
            return False, str(e)
    
    @staticmethod
    def prefix_to_mask(prefix_length: int) -> str:
        """
        将前缀长度转换为子网掩码
        
        Args:
            prefix_length: 前缀长度 (0-32)
            
        Returns:
            str: 子网掩码，如 "255.255.255.0"
        """
        if prefix_length < 0 or prefix_length > 32:
            return "0.0.0.0"
        
        mask_int = (0xFFFFFFFF << (32 - prefix_length)) & 0xFFFFFFFF
        return f"{(mask_int >> 24) & 0xFF}.{(mask_int >> 16) & 0xFF}.{(mask_int >> 8) & 0xFF}.{mask_int & 0xFF}"
    
    @staticmethod
    def mask_to_prefix(mask: str) -> int:
        """
        将子网掩码转换为前缀长度
        
        Args:
            mask: 子网掩码，如 "255.255.255.0"
            
        Returns:
            int: 前缀长度
        """
        try:
            parts = mask.split('.')
            if len(parts) != 4:
                return 0
            
            mask_int = (int(parts[0]) << 24) | (int(parts[1]) << 16) | (int(parts[2]) << 8) | int(parts[3])
            
            # 计算前缀长度
            prefix_length = 0
            for i in range(32):
                if mask_int & (1 << (31 - i)):
                    prefix_length += 1
                else:
                    break
            
            return prefix_length
        except Exception:
            return 0
    
    @staticmethod
    def validate_ip(ip: str) -> bool:
        """
        验证 IP 地址格式
        
        Args:
            ip: IP 地址字符串
            
        Returns:
            bool: 是否合法
        """
        pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(pattern, ip):
            return False
        
        parts = ip.split('.')
        for part in parts:
            if int(part) > 255:
                return False
        
        return True
    
    @staticmethod
    def validate_cidr(cidr: str) -> bool:
        """
        验证 CIDR 格式
        
        Args:
            cidr: CIDR 字符串，如 "192.168.1.0/24"
            
        Returns:
            bool: 是否合法
        """
        if '/' not in cidr:
            return False
        
        parts = cidr.split('/')
        if len(parts) != 2:
            return False
        
        ip, prefix = parts
        
        if not RouteManager.validate_ip(ip):
            return False
        
        try:
            prefix_int = int(prefix)
            if prefix_int < 0 or prefix_int > 32:
                return False
        except ValueError:
            return False
        
        return True
    
    @staticmethod
    def is_same_subnet(ip1: str, ip2: str, mask: str) -> bool:
        """
        检查两个 IP 是否在同一子网
        
        Args:
            ip1: IP 地址1
            ip2: IP 地址2
            mask: 子网掩码
            
        Returns:
            bool: 是否在同一子网
        """
        try:
            def ip_to_int(ip: str) -> int:
                parts = ip.split('.')
                return (int(parts[0]) << 24) | (int(parts[1]) << 16) | (int(parts[2]) << 8) | int(parts[3])
            
            ip1_int = ip_to_int(ip1)
            ip2_int = ip_to_int(ip2)
            mask_int = ip_to_int(mask)
            
            return (ip1_int & mask_int) == (ip2_int & mask_int)
        except Exception:
            return False


"""
接口管理模块 - 负责获取和管理网络接口信息
"""
import logging
from typing import List, Dict, Optional, Tuple
from utils.powershell import run_powershell_json

logger = logging.getLogger(__name__)


class NetworkInterface:
    """网络接口信息"""
    
    def __init__(self, data: dict):
        """
        初始化网络接口
        
        Args:
            data: PowerShell Get-NetAdapter 返回的接口数据
        """
        self.name = data.get('Name', '')
        self.if_index = data.get('ifIndex', 0)
        self.mac_address = data.get('MacAddress', '')
        self.status = data.get('Status', '')
        self.description = data.get('InterfaceDescription', '')
        
        # 网络配置信息（需要额外查询）
        self.ip_address = ''
        self.subnet_mask = ''
        self.gateway = ''
        self.prefix_length = 0
    
    def __repr__(self):
        return f"NetworkInterface(name={self.name}, ifIndex={self.if_index}, status={self.status})"


class InterfaceManager:
    """接口管理器"""
    
    def __init__(self):
        self.interfaces: List[NetworkInterface] = []
        self._name_to_interface: Dict[str, NetworkInterface] = {}
        self._index_to_interface: Dict[int, NetworkInterface] = {}
    
    def refresh_interfaces(self) -> bool:
        """
        刷新网络接口列表（仅获取 Up 状态的接口）
        
        Returns:
            bool: 是否成功
        """
        try:
            # 获取所有 Up 状态的网络适配器
            command = (
                "Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} | "
                "Select-Object Name, ifIndex, MacAddress, Status, InterfaceDescription | "
                "ConvertTo-Json"
            )
            
            success, data, error = run_powershell_json(command)
            
            if not success:
                logger.error(f"获取网络接口失败: {error}")
                return False
            
            # 清空现有接口列表
            self.interfaces.clear()
            self._name_to_interface.clear()
            self._index_to_interface.clear()
            
            # 处理返回的数据
            if data is None:
                logger.warning("没有找到活动的网络接口")
                return True
            
            # PowerShell 返回单个对象时不是数组
            if not isinstance(data, list):
                data = [data]
            
            # 创建接口对象
            for item in data:
                interface = NetworkInterface(item)
                self.interfaces.append(interface)
                self._name_to_interface[interface.name] = interface
                self._index_to_interface[interface.if_index] = interface
            
            logger.info(f"成功获取 {len(self.interfaces)} 个网络接口")
            
            # 获取每个接口的 IP 配置
            self._fetch_ip_config()
            
            return True
            
        except Exception as e:
            logger.error(f"刷新接口列表异常: {e}")
            return False
    
    def _fetch_ip_config(self):
        """获取接口的 IP 配置信息"""
        try:
            # 获取所有接口的 IP 配置
            command = (
                "Get-NetIPAddress -AddressFamily IPv4 | "
                "Select-Object ifIndex, IPAddress, PrefixLength | "
                "ConvertTo-Json"
            )
            
            success, data, error = run_powershell_json(command)
            
            if not success or data is None:
                logger.warning("获取 IP 配置失败")
                return
            
            # PowerShell 返回单个对象时不是数组
            if not isinstance(data, list):
                data = [data]
            
            # 更新接口的 IP 信息
            for item in data:
                if_index = item.get('ifIndex')
                if if_index in self._index_to_interface:
                    interface = self._index_to_interface[if_index]
                    interface.ip_address = item.get('IPAddress', '')
                    interface.prefix_length = item.get('PrefixLength', 0)
                    # 计算子网掩码
                    interface.subnet_mask = self._prefix_to_mask(interface.prefix_length)
            
            # 获取默认网关
            command = (
                "Get-NetRoute -AddressFamily IPv4 -DestinationPrefix '0.0.0.0/0' | "
                "Select-Object ifIndex, NextHop | "
                "ConvertTo-Json"
            )
            
            success, data, error = run_powershell_json(command)
            
            if success and data is not None:
                if not isinstance(data, list):
                    data = [data]
                
                for item in data:
                    if_index = item.get('ifIndex')
                    if if_index in self._index_to_interface:
                        interface = self._index_to_interface[if_index]
                        interface.gateway = item.get('NextHop', '')
            
        except Exception as e:
            logger.error(f"获取 IP 配置异常: {e}")
    
    @staticmethod
    def _prefix_to_mask(prefix_length: int) -> str:
        """
        将前缀长度转换为子网掩码
        
        Args:
            prefix_length: 前缀长度 (0-32)
            
        Returns:
            str: 子网掩码，如 "255.255.255.0"
        """
        if prefix_length < 0 or prefix_length > 32:
            return "0.0.0.0"
        
        # 计算掩码的整数值
        mask_int = (0xFFFFFFFF << (32 - prefix_length)) & 0xFFFFFFFF
        
        # 转换为 IP 地址格式
        return f"{(mask_int >> 24) & 0xFF}.{(mask_int >> 16) & 0xFF}.{(mask_int >> 8) & 0xFF}.{mask_int & 0xFF}"
    
    def get_interface_by_name(self, name: str) -> Optional[NetworkInterface]:
        """
        根据接口名称获取接口对象
        
        Args:
            name: 接口名称
            
        Returns:
            Optional[NetworkInterface]: 接口对象，未找到返回 None
        """
        return self._name_to_interface.get(name)
    
    def get_interface_by_index(self, if_index: int) -> Optional[NetworkInterface]:
        """
        根据 ifIndex 获取接口对象
        
        Args:
            if_index: 接口索引
            
        Returns:
            Optional[NetworkInterface]: 接口对象，未找到返回 None
        """
        return self._index_to_interface.get(if_index)
    
    def get_all_interfaces(self) -> List[NetworkInterface]:
        """
        获取所有接口列表
        
        Returns:
            List[NetworkInterface]: 接口列表
        """
        return self.interfaces.copy()
    
    def detect_wireguard(self) -> Tuple[bool, str]:
        """
        检测 WireGuard 全隧道模式
        
        Returns:
            Tuple[bool, str]: (是否检测到全隧道, 提示信息)
        """
        # 检查是否存在名为 "client" 的接口
        wg_interface = None
        for interface in self.interfaces:
            if 'wireguard' in interface.name.lower() or 'client' in interface.name.lower():
                wg_interface = interface
                break
        
        if wg_interface is None:
            return False, ""
        
        # 检查是否存在 0.0.0.0/1 和 128.0.0.0/1 路由
        try:
            command = (
                "Get-NetRoute -AddressFamily IPv4 | "
                "Where-Object {$_.DestinationPrefix -eq '0.0.0.0/1' -or $_.DestinationPrefix -eq '128.0.0.0/1'} | "
                "Select-Object DestinationPrefix, ifIndex | "
                "ConvertTo-Json"
            )
            
            success, data, error = run_powershell_json(command)
            
            if success and data is not None:
                if not isinstance(data, list):
                    data = [data]
                
                # 检查这些路由是否指向 WireGuard 接口
                for route in data:
                    if route.get('ifIndex') == wg_interface.if_index:
                        return True, (
                            f"检测到 WireGuard 全隧道模式 (接口: {wg_interface.name})。"
                            "建议直连白名单使用 /32 或精确 CIDR。"
                        )
        except Exception as e:
            logger.error(f"检测 WireGuard 异常: {e}")
        
        return False, ""


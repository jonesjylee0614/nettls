"""
校验工具模块 - 提供各种输入校验功能
"""
import re
import socket
import logging
from typing import Tuple, Optional
from core.route_manager import RouteManager

logger = logging.getLogger(__name__)


class Validator:
    """输入校验器"""
    
    @staticmethod
    def validate_ip(ip: str) -> Tuple[bool, str]:
        """
        验证 IP 地址格式
        
        Args:
            ip: IP 地址字符串
            
        Returns:
            Tuple[bool, str]: (是否合法, 错误信息)
        """
        if not ip:
            return False, "IP 地址不能为空"
        
        # 正则表达式验证
        pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(pattern, ip):
            return False, "IP 地址格式不正确"
        
        # 检查每个部分是否在 0-255 范围内
        parts = ip.split('.')
        for part in parts:
            try:
                num = int(part)
                if num < 0 or num > 255:
                    return False, f"IP 地址部分 {part} 超出范围 (0-255)"
            except ValueError:
                return False, f"IP 地址部分 {part} 不是有效数字"
        
        return True, ""
    
    @staticmethod
    def validate_cidr(cidr: str) -> Tuple[bool, str, int]:
        """
        验证 CIDR 格式
        
        Args:
            cidr: CIDR 字符串，如 "192.168.1.0/24"
            
        Returns:
            Tuple[bool, str, int]: (是否合法, 错误信息, 前缀长度)
        """
        if not cidr:
            return False, "CIDR 不能为空", 0
        
        # 检查是否包含 /
        if '/' not in cidr:
            return False, "CIDR 格式错误，缺少 '/'", 0
        
        parts = cidr.split('/')
        if len(parts) != 2:
            return False, "CIDR 格式错误，只能有一个 '/'", 0
        
        ip, prefix = parts
        
        # 验证 IP 部分
        valid, error = Validator.validate_ip(ip)
        if not valid:
            return False, error, 0
        
        # 验证前缀长度
        try:
            prefix_int = int(prefix)
            if prefix_int < 0 or prefix_int > 32:
                return False, f"前缀长度 {prefix_int} 超出范围 (0-32)", 0
        except ValueError:
            return False, f"前缀长度 {prefix} 不是有效数字", 0
        
        return True, "", prefix_int
    
    @staticmethod
    def validate_target(target: str) -> Tuple[bool, str, str]:
        """
        验证目标地址（支持 IP、CIDR、域名）
        
        Args:
            target: 目标地址
            
        Returns:
            Tuple[bool, str, str]: (是否合法, 错误信息, 类型:ip/cidr/domain)
        """
        if not target:
            return False, "目标地址不能为空", ""
        
        # 尝试解析为 CIDR
        if '/' in target:
            valid, error, _ = Validator.validate_cidr(target)
            if valid:
                return True, "", "cidr"
            else:
                return False, error, ""
        
        # 尝试解析为 IP
        valid, error = Validator.validate_ip(target)
        if valid:
            return True, "", "ip"
        
        # 尝试解析为域名
        if Validator._is_valid_domain(target):
            return True, "", "domain"
        
        return False, "目标地址格式不正确（不是有效的 IP、CIDR 或域名）", ""
    
    @staticmethod
    def _is_valid_domain(domain: str) -> bool:
        """
        检查是否是有效的域名格式
        
        Args:
            domain: 域名字符串
            
        Returns:
            bool: 是否有效
        """
        # 域名正则表达式
        pattern = r'^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'
        return bool(re.match(pattern, domain))
    
    @staticmethod
    def resolve_domain(domain: str) -> Tuple[bool, list, str]:
        """
        解析域名为 IP 地址
        
        Args:
            domain: 域名
            
        Returns:
            Tuple[bool, list, str]: (是否成功, IP列表, 错误信息)
        """
        try:
            # 使用 socket.getaddrinfo 解析域名
            results = socket.getaddrinfo(domain, None, socket.AF_INET)
            
            # 提取 IP 地址并去重
            ip_list = list(set([result[4][0] for result in results]))
            
            if not ip_list:
                return False, [], "域名解析失败，未返回 IP 地址"
            
            return True, ip_list, ""
            
        except socket.gaierror as e:
            logger.error(f"域名解析失败: {domain}, 错误: {e}")
            return False, [], f"域名解析失败: {e}"
        except Exception as e:
            logger.error(f"域名解析异常: {domain}, 错误: {e}")
            return False, [], f"域名解析异常: {e}"
    
    @staticmethod
    def validate_gateway(gateway: str, interface_ip: str, interface_mask: str) -> Tuple[bool, str]:
        """
        验证网关是否与接口在同一网段
        
        Args:
            gateway: 网关 IP
            interface_ip: 接口 IP
            interface_mask: 接口子网掩码
            
        Returns:
            Tuple[bool, str]: (是否合法, 错误信息)
        """
        # 验证网关 IP 格式
        valid, error = Validator.validate_ip(gateway)
        if not valid:
            return False, f"网关 IP 格式错误: {error}"
        
        # 验证接口 IP 格式
        valid, error = Validator.validate_ip(interface_ip)
        if not valid:
            return False, f"接口 IP 格式错误: {error}"
        
        # 验证接口掩码格式
        valid, error = Validator.validate_ip(interface_mask)
        if not valid:
            return False, f"接口掩码格式错误: {error}"
        
        # 检查是否在同一网段
        if not RouteManager.is_same_subnet(gateway, interface_ip, interface_mask):
            return False, f"网关 {gateway} 与接口 {interface_ip}/{interface_mask} 不在同一网段"
        
        return True, ""
    
    @staticmethod
    def validate_metric(metric: str) -> Tuple[bool, str, int]:
        """
        验证 Metric 值
        
        Args:
            metric: Metric 字符串
            
        Returns:
            Tuple[bool, str, int]: (是否合法, 错误信息, Metric值)
        """
        if not metric:
            return False, "Metric 不能为空", 0
        
        try:
            metric_int = int(metric)
            if metric_int < 1 or metric_int > 999:
                return False, f"Metric {metric_int} 超出范围 (1-999)", 0
            
            return True, "", metric_int
            
        except ValueError:
            return False, f"Metric {metric} 不是有效数字", 0
    
    @staticmethod
    def is_dangerous_route(target: str) -> Tuple[bool, str]:
        """
        检查是否是危险路由（默认路由、本地网段等）
        
        Args:
            target: 目标地址
            
        Returns:
            Tuple[bool, str]: (是否危险, 警告信息)
        """
        # 提取 IP 部分
        ip = target.split('/')[0] if '/' in target else target
        
        # 默认路由
        if ip == "0.0.0.0":
            return True, "警告: 修改默认路由 (0.0.0.0/0) 可能导致网络中断"
        
        # Loopback
        if ip.startswith("127."):
            return True, "警告: 修改 Loopback 路由可能影响本地服务"
        
        # 链路本地地址
        if ip.startswith("169.254."):
            return True, "警告: 修改链路本地地址路由可能影响网络发现"
        
        # 组播地址
        if ip.startswith("224.") or ip.startswith("239."):
            return True, "警告: 修改组播路由可能影响组播服务"
        
        return False, ""
    
    @staticmethod
    def validate_description(desc: str, required: bool = False) -> Tuple[bool, str]:
        """
        验证描述信息
        
        Args:
            desc: 描述文本
            required: 是否必填
            
        Returns:
            Tuple[bool, str]: (是否合法, 错误信息)
        """
        if required and not desc.strip():
            return False, "描述不能为空"
        
        if len(desc) > 200:
            return False, "描述长度不能超过 200 个字符"
        
        return True, ""


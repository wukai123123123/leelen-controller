#!/usr/bin/env python3

import leelen
from random import randint
import socket
import time


def discover_device_simple(device_number, local_ip=None, timeout=3.0):
    """
    简单的设备发现功能 - 不使用线程
    """
    port = 6789
    groupaddr = '224.0.0.1'
    
    print(f"正在发现设备: {device_number}")
    print(f"组播地址: {groupaddr}:{port}")
    
    # 创建UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(timeout)
    
    try:
        # 绑定到端口
        sock.bind(('0.0.0.0', port))
        
        # 发送发现请求
        target_num = leelen.Number(device_number)
        print(f"发送发现请求到: {target_num}")
        sock.sendto(str(target_num).encode(), (groupaddr, port))
        
        # 等待响应
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                data, addr = sock.recvfrom(1500)
                print(f"\n收到来自 {addr} 的数据: {data}")
                
                try:
                    msg = data.decode()
                    if '?' in msg:
                        ip = msg.split('?', 1)[0]
                        print(f"发现设备: {device_number} -> {ip}")
                        print(f"完整响应: {msg}")
                        return ip
                except Exception as e:
                    print(f"解码响应数据时出错: {e}, 数据: {data}")
                    
            except socket.timeout:
                continue
                
        print(f"未发现设备: {device_number}")
        return None
        
    finally:
        sock.close()


def scan_network():
    """
    扫描网络查找立林设备
    """
    print("=" * 60)
    print("网络扫描模式")
    print("=" * 60)
    print("\n正在扫描常见的立林设备IP段...")
    
    # 常见的门口机编号
    common_numbers = [
        "0001-0000", "0001-0001", "0001-0002",
        "0000-0001", "0000-0000",
        "9999-0001"  # 管理机
    ]
    
    for num in common_numbers:
        print(f"\n尝试发现: {num}")
        ip = discover_device_simple(num, timeout=2)
        if ip:
            print(f"\n成功发现设备！")
            return ip, num
            
    print("\n未发现任何设备")
    return None, None


def test_unlock(doorway_ip, doorway_number, local_number, position=4):
    """
    测试远程开锁功能
    
    参数:
        doorway_ip: 门口机IP地址
        doorway_number: 门口机编号 (如 "0001-0000")
        local_number: 本机号码 (如 "0601-1101")
        position: 门位置 (默认为4)
    """
    print(f"开始测试远程开锁...")
    print(f"本机号码: {local_number}")
    print(f"门口机IP: {doorway_ip}")
    print(f"门口机编号: {doorway_number}")
    print(f"门位置: {position}")
    
    try:
        # 创建远程开锁命令
        unlock_cmd = leelen.ControlMessage(
            protocol_version=0x0301,
            command=leelen.ControlCommand.REMOTE_UNLOCK,
            id=randint(0, 0xffff),
            is_ack=False,
            is_encrypt=False,
            src=leelen.Number(local_number),
            dst=leelen.Number(doorway_number),
            body=leelen.Req0109(position=position)
        )
        
        print(f"\n发送开锁命令...")
        print(f"命令包: {unlock_cmd.pack().hex()}")
        print(f"命令包长度: {len(unlock_cmd.pack())} 字节")
        
        # 发送命令
        response = leelen.control(doorway_ip, unlock_cmd.pack(), timeout=2.0)
        print(f"收到响应: {response.hex()}")
        
        # 解析响应
        try:
            resp_msg = leelen.ControlMessage.unpack(response)
            print(f"响应命令: {resp_msg.command}")
            print(f"是否ACK: {resp_msg.is_ack}")
            print("开锁测试成功！")
        except Exception as e:
            print(f"响应解析失败: {e}")
            print("但命令已发送，可能已成功开锁")
            
        return True
        
    except socket.timeout:
        print("超时: 未收到设备响应")
        print("请检查:")
        print("1. 门口机IP地址是否正确")
        print("2. 网络连接是否正常")
        print("3. 门口机是否在线")
        return False
    except Exception as e:
        print(f"发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def get_local_ip():
    """
    获取本机IP地址
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        print(f"获取本机IP地址时出错: {e}")
        return None


if __name__ == "__main__":
    print("=" * 60)
    print("立林门禁远程开锁测试工具")
    print("=" * 60)
    
    # 小区配置信息
    LOCAL_IP = "192.168.6.112"
    LOCAL_NUMBER = "0601-1101"
    MANAGER_NUMBER = "9999-0001"
    
    print(f"\n本机配置:")
    print(f"  IP地址: {LOCAL_IP}")
    print(f"  本机号码: {LOCAL_NUMBER}")
    print(f"  管理机号码: {MANAGER_NUMBER}")
    
    # 尝试获取本机实际IP
    actual_ip = get_local_ip()
    if actual_ip and actual_ip != LOCAL_IP:
        print(f"  检测到实际IP: {actual_ip}")
    
    print("\n" + "=" * 60)
    print("请选择操作:")
    print("1. 扫描网络发现设备")
    print("2. 指定设备编号发现")
    print("3. 直接测试开门")
    print("=" * 60)
    
    choice = input("\n请输入选项 (1/2/3, 默认3): ").strip() or "3"
    
    discovered_ip = None
    discovered_number = None
    
    if choice == "1":
        # 扫描网络模式
        discovered_ip, discovered_number = scan_network()
        
    elif choice == "2":
        # 指定编号发现
        print("\n指定设备编号发现模式")
        print("-" * 60)
        target_number = input("请输入要发现的设备编号 (如 0001-0000): ").strip()
        if not target_number:
            target_number = "0001-0000"
        discovered_ip = discover_device_simple(target_number)
        if discovered_ip:
            discovered_number = target_number
    
    # 如果发现了设备，询问是否直接开门
    if discovered_ip and discovered_number:
        print("\n" + "=" * 60)
        use_discovered = input("是否使用发现的设备进行开门测试? (Y/n): ").strip().lower()
        if use_discovered != "n":
            doorway_ip = discovered_ip
            doorway_number = discovered_number
            position = input("请输入门位置 (默认 4): ").strip()
            position = int(position) if position else 4
            
            print("\n" + "-" * 60)
            test_unlock(doorway_ip, doorway_number, LOCAL_NUMBER, position)
            print("-" * 60)
            exit(0)
    
    # 直接开门模式
    if choice == "3" or not discovered_ip:
        print("\n直接开门模式")
        print("-" * 60)
        doorway_ip = input("请输入门口机IP地址: ").strip()
        if not doorway_ip:
            print("错误: 必须输入门口机IP地址")
            exit(1)
            
        doorway_number = input("请输入门口机编号 (默认 0001-0000): ").strip() or "0001-0000"
        position = input("请输入门位置 (默认 4): ").strip()
        position = int(position) if position else 4
        
        print("\n" + "=" * 60)
        confirm = input("确认开始测试开锁? (y/N): ").strip().lower()
        if confirm == "y":
            print("\n" + "-" * 60)
            test_unlock(doorway_ip, doorway_number, LOCAL_NUMBER, position)
            print("-" * 60)
        else:
            print("已取消操作")

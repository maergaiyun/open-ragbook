#!/usr/bin/env python3
"""
依赖安装脚本
根据系统GPU情况自动选择CPU或GPU版本的PyTorch依赖
"""

import subprocess
import sys
import os
import platform

def run_command(command, check=True):
    """执行命令并返回结果"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=check)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return False, e.stdout, e.stderr

def check_nvidia_gpu():
    """检查是否有NVIDIA GPU"""
    print("检查NVIDIA GPU...")
    
    # 检查nvidia-smi命令
    success, stdout, stderr = run_command("nvidia-smi", check=False)
    if success and "NVIDIA" in stdout:
        print("检测到NVIDIA GPU")
        return True
    
    # 在Windows上检查wmic
    if platform.system() == "Windows":
        success, stdout, stderr = run_command('wmic path win32_VideoController get name', check=False)
        if success and "NVIDIA" in stdout:
            print("检测到NVIDIA GPU (通过wmic)")
            return True
    
    print("未检测到NVIDIA GPU")
    return False

def check_cuda_available():
    """检查CUDA是否可用"""
    print("检查CUDA可用性...")
    
    try:
        # 尝试导入torch并检查CUDA
        import torch
        if torch.cuda.is_available():
            print(f"CUDA可用，设备数量: {torch.cuda.device_count()}")
            return True
        else:
            print("CUDA不可用")
            return False
    except ImportError:
        print("PyTorch未安装，无法检查CUDA")
        return None

def install_basic_requirements():
    """安装基础依赖"""
    print("安装基础依赖...")
    success, stdout, stderr = run_command("pip install -r requirements.txt")
    if success:
        print("基础依赖安装完成")
        return True
    else:
        print(f"基础依赖安装失败: {stderr}")
        return False

def install_pytorch_cpu():
    """安装CPU版本的PyTorch"""
    print("安装CPU版本的PyTorch...")
    pytorch_cpu_packages = [
        "torch==2.7.1+cpu",
        "torchaudio==2.7.1+cpu", 
        "torchvision==0.22.1+cpu"
    ]
    
    # 使用PyTorch官方CPU索引
    cmd = f"pip install {' '.join(pytorch_cpu_packages)} --index-url https://download.pytorch.org/whl/cpu"
    success, stdout, stderr = run_command(cmd)
    
    if success:
        print("CPU版本PyTorch安装完成")
        return True
    else:
        print(f"CPU版本PyTorch安装失败: {stderr}")
        return False

def install_pytorch_gpu():
    """安装GPU版本的PyTorch"""
    print("安装GPU版本的PyTorch...")
    pytorch_gpu_packages = [
        "torch==2.5.1+cu121",
        "torchaudio==2.5.1+cu121",
        "torchvision==0.20.1+cu121"
    ]
    
    # 添加GPU工具
    gpu_packages = pytorch_gpu_packages + ["GPUtil==1.4.0"]
    
    # 使用PyTorch官方CUDA索引
    cmd = f"pip install {' '.join(gpu_packages)} --index-url https://download.pytorch.org/whl/cu121"
    success, stdout, stderr = run_command(cmd)
    
    if success:
        print("GPU版本PyTorch安装完成")
        return True
    else:
        print(f"GPU版本PyTorch安装失败: {stderr}")
        return False

def verify_installation():
    """验证安装"""
    print("验证安装...")
    
    try:
        import torch
        print(f"PyTorch版本: {torch.__version__}")
        
        if torch.cuda.is_available():
            print(f"CUDA版本: {torch.version.cuda}")
            print(f"GPU设备数量: {torch.cuda.device_count()}")
            for i in range(torch.cuda.device_count()):
                print(f"   - GPU {i}: {torch.cuda.get_device_name(i)}")
        else:
            print("使用CPU版本")
            
        return True
    except ImportError as e:
        print(f"PyTorch导入失败: {e}")
        return False

def main():
    """主函数"""
    print("开始依赖安装...")
    print("=" * 50)
    
    # 检查Python版本
    python_version = sys.version_info
    print(f"Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    if python_version < (3, 12):
        print("错误: 需要Python 3.12或更高版本")
        sys.exit(1)
    
    # 安装基础依赖
    if not install_basic_requirements():
        print("基础依赖安装失败，退出")
        sys.exit(1)
    
    print("\n" + "=" * 50)
    
    # 检查GPU情况
    has_nvidia_gpu = check_nvidia_gpu()
    cuda_available = check_cuda_available()
    
    print("\n" + "=" * 50)
    
    # 决定安装策略
    if has_nvidia_gpu:
        print("检测到NVIDIA GPU，将安装GPU版本的PyTorch")
        if not install_pytorch_gpu():
            print("GPU版本安装失败，尝试安装CPU版本...")
            if not install_pytorch_cpu():
                print("所有PyTorch安装尝试都失败了")
                sys.exit(1)
    else:
        print("未检测到NVIDIA GPU，将安装CPU版本的PyTorch")
        if not install_pytorch_cpu():
            print("CPU版本PyTorch安装失败")
            sys.exit(1)
    
    print("\n" + "=" * 50)
    
    # 验证安装
    if verify_installation():
        print("\n所有依赖安装完成！")
        print("\n安装总结:")
        print("   - 基础依赖")
        print("   - PyTorch (CPU/GPU版本)")
        print("   - 其他AI/ML库")
        print("\n现在可以启动应用了！")
    else:
        print("\n安装验证失败，请检查错误信息")
        sys.exit(1)

if __name__ == "__main__":
    main() 
import os
import time
import datetime
import sys
from logging.handlers import TimedRotatingFileHandler

class DailyRotatingFileHandler(TimedRotatingFileHandler):
    """
    自定义日志处理器，结合了TimeRotating和Size两种切割特性:
    1. 按照日期创建子目录存储日志
    2. 每天创建新的日志文件
    3. 如果单个日志文件超过指定大小，则进行分块
    """

    def __init__(self, filename, when='midnight', interval=1, backupCount=30, maxBytes=10*1024*1024,
                 encoding=None, delay=False, utc=False, atTime=None):
        """
        初始化处理器
        :param filename: 日志文件基础名称，不包含路径
        :param when: 时间切割单位
        :param interval: 切割时间间隔
        :param backupCount: 备份文件数量
        :param maxBytes: 单个文件最大大小(字节)
        :param encoding: 编码
        :param delay: 延迟创建文件
        :param utc: 使用UTC时间
        :param atTime: 指定时间
        """
        self.base_filename = filename
        self.maxBytes = maxBytes
        self._size_files_count = 0  # 当天按大小切割的文件计数
        
        # 获取实际的日志文件路径(按日期创建子目录)
        actual_path = self._get_log_path()
        print(f"初始化日志文件路径: {actual_path}")
        
        # 创建目录
        self._ensure_dir_exists(os.path.dirname(actual_path))
        
        TimedRotatingFileHandler.__init__(self, actual_path, when, interval, backupCount,
                                         encoding, delay, utc, atTime)

    def _ensure_dir_exists(self, dir_path):
        """确保目录存在，如果不存在则创建"""
        try:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
                print(f"创建日志目录: {dir_path}")
        except Exception as e:
            print(f"创建日志目录失败: {dir_path}, 错误: {str(e)}", file=sys.stderr)

    def _get_log_path(self):
        """
        获取当前日期的日志目录和完整文件路径
        """
        # 获取项目根目录下的logs目录
        try:
            base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
            today = datetime.datetime.now().strftime('%Y-%m-%d')
            log_dir = os.path.join(base_dir, today)
            
            # 确保日志目录存在
            self._ensure_dir_exists(log_dir)
            
            log_path = os.path.join(log_dir, self.base_filename)
            print(f"计算日志路径: {log_path}")
            return log_path
        except Exception as e:
            print(f"日志路径计算错误: {str(e)}", file=sys.stderr)
            # 回退到默认路径
            fallback_path = os.path.join(os.getcwd(), 'logs', self.base_filename)
            self._ensure_dir_exists(os.path.dirname(fallback_path))
            return fallback_path

    def shouldRollover(self, record):
        """
        检查是否应该滚动日志文件，满足两个条件之一：
        1. 超过大小限制
        2. 到达时间点
        """
        # 检查是否超过大小限制
        if self.maxBytes > 0:
            try:
                # 检查文件大小
                if os.path.exists(self.baseFilename):
                    size = os.path.getsize(self.baseFilename)
                    if size >= self.maxBytes:
                        print(f"日志文件 {self.baseFilename} 大小 {size} 超过限制 {self.maxBytes}，触发滚动")
                        return True
            except Exception as e:
                print(f"检查日志文件大小失败: {str(e)}", file=sys.stderr)
                
        # 检查时间是否达到滚动点
        should_roll = TimedRotatingFileHandler.shouldRollover(self, record)
        if should_roll:
            print(f"时间触发日志滚动，当前文件: {self.baseFilename}")
        return should_roll

    def rotation_filename(self, default_name):
        """
        生成滚动文件名
        - 如果是按时间滚动，使用标准的时间后缀
        - 如果是按大小滚动，使用数字后缀
        """
        # 检查是否当前文件大小超过限制
        if os.path.exists(self.baseFilename) and os.path.getsize(self.baseFilename) >= self.maxBytes:
            # 按大小滚动情况下使用数字后缀
            self._size_files_count += 1
            dirname, basename = os.path.split(self.baseFilename)
            name, ext = os.path.splitext(basename)
            new_name = os.path.join(dirname, f"{name}.{self._size_files_count}{ext}")
            print(f"按大小滚动，新文件名: {new_name}")
            return new_name
        
        # 按时间滚动情况使用父类方法
        result = TimedRotatingFileHandler.rotation_filename(self, default_name)
        print(f"按时间滚动，新文件名: {result}")
        return result

    def doRollover(self):
        """
        执行日志滚动
        - 如果是因为文件大小而滚动，只执行大小相关的滚动
        - 如果是因为时间而滚动，则重新计算文件路径并执行父类滚动
        """
        # 检查是否因文件大小触发滚动
        if os.path.exists(self.baseFilename) and os.path.getsize(self.baseFilename) >= self.maxBytes:
            print(f"执行大小滚动，文件: {self.baseFilename}")
            # 按大小滚动
            if self.stream:
                self.stream.close()
                self.stream = None
                
            # 重命名当前文件
            dfn = self.rotation_filename(self.baseFilename)
            if os.path.exists(dfn):
                os.remove(dfn)
            os.rename(self.baseFilename, dfn)
            
            # 创建新文件
            self.mode = 'a'
            self.stream = self._open()
            return
        
        # 如果是时间触发，则重新计算日志路径，时间滚动时可能需要创建新的日期子目录
        old_base = self.baseFilename
        self.baseFilename = self._get_log_path()
        self._size_files_count = 0  # 重置分块计数
        
        print(f"时间滚动，旧文件: {old_base} -> 新文件: {self.baseFilename}")
        
        # 如果路径发生变化（新的日期），则直接关闭旧文件，创建新文件
        if old_base != self.baseFilename:
            print(f"日期变更，关闭旧文件，创建新文件")
            if self.stream:
                self.stream.close()
                self.stream = None
            self.mode = 'a'
            self.stream = self._open()
            return
            
        # 执行父类的滚动操作
        print(f"执行时间滚动但路径未变")
        TimedRotatingFileHandler.doRollover(self) 
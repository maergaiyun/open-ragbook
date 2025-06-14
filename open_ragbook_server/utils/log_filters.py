import logging

class ColorLogFilter(logging.Filter):
    """为日志级别添加颜色代码，用于终端彩色输出"""
    
    # ANSI颜色代码
    COLORS = {
        'DEBUG': '36',     # 青色
        'INFO': '32',      # 绿色
        'WARNING': '33',   # 黄色
        'ERROR': '31',     # 红色
        'CRITICAL': '35',  # 紫色
    }
    
    def filter(self, record):
        # 添加颜色代码到记录属性
        levelname = record.levelname
        record.levelcolor = self.COLORS.get(levelname, '37')  # 默认白色
        return True 
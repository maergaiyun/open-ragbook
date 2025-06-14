from datetime import datetime


def rows_datetime_format(rows, date_fields=None):
    """转换成yyyy-mm-dd HH:MM:SS格式给前端"""
    if rows:
        # 默认日期字段列表，如果没有传入date_fields，则会处理created_at和updated_at
        date_fields = date_fields or ['created_at', 'updated_at']

        for item in rows:
            for field in date_fields:
                if field in item and isinstance(item[field], datetime):
                    item[field] = item[field].strftime("%Y-%m-%d %H:%M:%S")

    return rows

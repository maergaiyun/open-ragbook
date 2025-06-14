/**
 * 日期格式化函数
 * @param {Date|string|number} date 要格式化的日期，可以是 Date 对象、时间戳或日期字符串
 * @param {string} [format='YYYY-MM-DD HH:mm:ss'] 格式化模式
 * @returns {string} 格式化后的日期字符串
 */
export function formatDate(date, format = 'YYYY-MM-DD HH:mm:ss') {
  if (!date) return '';
  
  // 确保日期是 Date 对象
  let dateObj = date;
  if (typeof date === 'string' || typeof date === 'number') {
    dateObj = new Date(date);
  }
  
  // 如果日期无效，返回空字符串
  if (isNaN(dateObj.getTime())) {
    console.warn('Invalid date:', date);
    return '';
  }
  
  const year = dateObj.getFullYear();
  const month = dateObj.getMonth() + 1;
  const day = dateObj.getDate();
  const hours = dateObj.getHours();
  const minutes = dateObj.getMinutes();
  const seconds = dateObj.getSeconds();
  
  // 补零函数
  const padZero = (num) => (num < 10 ? '0' + num : num);
  
  return format
    .replace(/YYYY/g, year)
    .replace(/MM/g, padZero(month))
    .replace(/DD/g, padZero(day))
    .replace(/HH/g, padZero(hours))
    .replace(/mm/g, padZero(minutes))
    .replace(/ss/g, padZero(seconds));
}

/**
 * 格式化为相对时间（如：几分钟前，几小时前）
 * @param {Date|string|number} date 日期或时间戳
 * @returns {string} 相对时间字符串
 */
export function formatRelativeTime(date) {
  if (!date) return '';
  
  const dateObj = typeof date === 'object' ? date : new Date(date);
  const now = new Date();
  const diff = now - dateObj;
  
  // 时间差（毫秒）
  const minute = 60 * 1000;
  const hour = 60 * minute;
  const day = 24 * hour;
  const week = 7 * day;
  const month = 30 * day;
  
  if (diff < minute) {
    return '刚刚';
  } else if (diff < hour) {
    return Math.floor(diff / minute) + '分钟前';
  } else if (diff < day) {
    return Math.floor(diff / hour) + '小时前';
  } else if (diff < week) {
    return Math.floor(diff / day) + '天前';
  } else if (diff < month) {
    return Math.floor(diff / week) + '周前';
  } else {
    return formatDate(dateObj, 'YYYY-MM-DD');
  }
} 
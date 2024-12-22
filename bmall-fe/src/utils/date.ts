/**
 * 将 UTC 时间转换为北京时间
 * @param dateStr UTC 时间字符串
 * @param format 是否格式化输出
 * @returns 格式化的时间字符串或 Date 对象
 */
export function toBeijingTime(dateStr: string, format = true): string | Date {
  const utcDate = new Date(dateStr)
  const beijingDate = new Date(utcDate.getTime() + 8 * 60 * 60 * 1000)
  
  if (!format) {
    return beijingDate
  }
  
  return beijingDate.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  })
}

/**
 * 简短格式的北京时间
 * @param dateStr UTC 时间字符串
 * @returns 格式化的时间字符串
 */
export function toShortBeijingTime(dateStr: string): string {
  const beijingDate = toBeijingTime(dateStr, false) as Date
  return beijingDate.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  })
} 
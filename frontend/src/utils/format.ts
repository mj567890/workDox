import dayjs from 'dayjs'

export function formatDate(date: string | Date | null | undefined, format = 'YYYY-MM-DD HH:mm'): string {
  if (!date) return '-'
  return dayjs(date).format(format)
}

export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

export function formatPercent(value: number): string {
  return (value * 100).toFixed(1) + '%'
}

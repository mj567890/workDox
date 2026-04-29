export const DOCUMENT_STATUS = {
  draft: { label: '草稿', color: 'info' },
  submitted: { label: '已提交', color: '' },
  reviewing: { label: '审批中', color: 'warning' },
  approved: { label: '已批准', color: 'success' },
  rejected: { label: '已驳回', color: 'danger' },
  official: { label: '正式版', color: 'success' },
  signed: { label: '已签批', color: '' },
  archived: { label: '已归档', color: 'warning' },
  conflict: { label: '冲突', color: 'danger' },
} as const

export const MATTER_STATUS = {
  pending: { label: '待开始', color: 'info' },
  in_progress: { label: '进行中', color: '' },
  paused: { label: '已暂停', color: 'warning' },
  completed: { label: '已完成', color: 'success' },
  cancelled: { label: '已取消', color: 'danger' },
} as const

export const TASK_PRIORITY = {
  low: { label: '低', color: 'info' },
  normal: { label: '普通', color: '' },
  high: { label: '高', color: 'warning' },
  urgent: { label: '紧急', color: 'danger' },
} as const

export const TASK_STATUS = {
  pending: { label: '待处理', color: 'info' },
  in_progress: { label: '处理中', color: '' },
  completed: { label: '已完成', color: 'success' },
  cancelled: { label: '已取消', color: 'danger' },
} as const

export const NODE_STATUS = {
  pending: { label: '待处理', color: 'info' },
  in_progress: { label: '进行中', color: '' },
  completed: { label: '已完成', color: 'success' },
  skipped: { label: '已跳过', color: 'warning' },
  rolled_back: { label: '已退回', color: 'danger' },
} as const

export const FILE_TYPE_ICONS: Record<string, string> = {
  docx: 'Document',
  doc: 'Document',
  xlsx: 'Grid',
  xls: 'Grid',
  pptx: 'Presentation',
  ppt: 'Presentation',
  pdf: 'Document',
  txt: 'Edit',
  md: 'Edit',
  csv: 'Grid',
  jpg: 'Picture',
  jpeg: 'Picture',
  png: 'Picture',
  gif: 'Picture',
  bmp: 'Picture',
  zip: 'FolderOpened',
  rar: 'FolderOpened',
  '7z': 'FolderOpened',
}

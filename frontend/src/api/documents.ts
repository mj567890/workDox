import { get, post, put, del } from './index'

export interface DocumentItem {
  id: number
  original_name: string
  file_type: string
  file_size: number
  mime_type: string
  description: string | null
  owner_id: number
  owner_name: string
  matter_id: number | null
  matter_title: string | null
  category_id: number | null
  category_name: string | null
  status: string
  current_version_id: number | null
  current_version_no: number | null
  permission_scope: string
  tags: TagItem[]
  is_locked: boolean
  locked_by_name: string | null
  preview_pdf_path: string | null
  extracted_text_length: number | null
  created_at: string
  updated_at: string
}

export interface TagItem {
  id: number
  name: string
  color: string
}

export interface CategoryItem {
  id: number
  name: string
  code: string
  description: string | null
  sort_order: number
  is_system: boolean
  document_count: number
}

export interface DocumentVersion {
  id: number
  document_id: number
  version_no: number
  file_size: number
  upload_user_id: number
  upload_user_name: string
  change_note: string | null
  is_official: boolean
  checksum: string | null
  created_at: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface LockStatus {
  locked: boolean
  locked_by: string | null
  locked_at: string | null
  expires_at: string | null
}

export interface DocumentReview {
  id: number
  document_id: number
  review_level: number
  reviewer_id: number
  reviewer_name: string | null
  status: string  // pending | approved | rejected
  comment: string | null
  reviewed_at: string | null
  created_at: string | null
}

export interface PendingReview {
  id: number
  document_id: number
  document_name: string | null
  document_owner: string | null
  review_level: number
  status: string
  created_at: string | null
}

export interface SimilarDocument {
  document_id: number
  original_name: string
  file_type: string
  description: string | null
  status: string
  similarity_score: number
  headline: string | null
}

export interface GraphNode {
  id: string
  name: string
  type: string
  symbolSize: number
  category: number
}

export interface GraphLink {
  source: string
  target: string
  label: string
}

export interface PreviewText {
  content: string | null
  format: 'markdown' | 'text' | 'html'
  has_content: boolean
  detail?: string
  can_generate_html?: boolean
}

export interface GraphData {
  nodes: GraphNode[]
  links: GraphLink[]
  categories: { name: string }[]
}

export interface CategorySuggestion {
  category_id: number
  category_name: string
  score: number
}

export interface TagSuggestion {
  tag_id: number
  tag_name: string
  matched_keyword: string
}

export const documentsApi = {
  getList: (params?: Record<string, any>) => get<PaginatedResponse<DocumentItem>>('/documents', params),
  getDetail: (id: number) => get<DocumentItem>(`/documents/${id}`),
  update: (id: number, data: Record<string, any>) => put<DocumentItem>(`/documents/${id}`, data),
  delete: (id: number) => del(`/documents/${id}`),
  upload: (data: FormData) => post<DocumentItem>('/documents/upload', data, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  download: (id: number) => get<Blob>(`/documents/${id}/download`),
  getPreview: (id: number) => get<{ url: string; status: string }>(`/documents/${id}/preview`),
  getPreviewText: (id: number) => get<PreviewText>(`/documents/${id}/preview-text`),
  generatePreview: (id: number) => post(`/documents/${id}/generate-preview`),
  getVersions: (id: number) => get<DocumentVersion[]>(`/documents/${id}/versions`),
  uploadVersion: (id: number, data: FormData) => post<DocumentVersion>(`/documents/${id}/versions`, data, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  setOfficialVersion: (id: number, vid: number) => put(`/documents/${id}/versions/${vid}/official`),
  lock: (id: number) => post<LockStatus>(`/documents/${id}/lock`),
  unlock: (id: number) => del(`/documents/${id}/lock`),
  getLockStatus: (id: number) => get<LockStatus>(`/documents/${id}/lock-status`),
  getCategories: () => get<CategoryItem[]>('/documents/categories'),
  createCategory: (data: Record<string, any>) => post<CategoryItem>('/documents/categories', data),
  updateCategory: (id: number, data: Record<string, any>) => put(`/documents/categories/${id}`, data),
  deleteCategory: (id: number) => del(`/documents/categories/${id}`),
  getTags: () => get<TagItem[]>('/documents/tags'),
  createTag: (data: Record<string, any>) => post<TagItem>('/documents/tags', data),
  deleteTag: (id: number) => del(`/documents/tags/${id}`),
  addReference: (id: number, data: { matter_id: number; is_readonly: boolean }) => post(`/documents/${id}/reference`, data),
  getReferences: (id: number) => get(`/documents/${id}/references`),
  removeReference: (id: number, refId: number) => del(`/documents/${id}/references/${refId}`),

  // Approval workflow
  submitForReview: (id: number, reviewerIds: number[]) =>
    post<DocumentItem>(`/documents/${id}/submit-review`, { reviewer_ids: reviewerIds }),
  approve: (id: number, reviewLevel: number, comment?: string) =>
    post<DocumentReview>(`/documents/${id}/approve/${reviewLevel}`, { comment }),
  reject: (id: number, reviewLevel: number, comment?: string) =>
    post<DocumentReview>(`/documents/${id}/reject/${reviewLevel}`, { comment }),
  getReviews: (id: number) => get<DocumentReview[]>(`/documents/${id}/reviews`),
  getMyPendingReviews: () => get<PendingReview[]>('/documents/pending-reviews/mine'),

  // Document intelligence
  extractText: (id: number) => post<{ detail: string; extracted: boolean; length?: number }>(`/documents/${id}/extract-text`),
  getSimilarDocuments: (id: number, limit?: number) => get<SimilarDocument[]>(`/documents/${id}/similar`, { limit }),
  getDocumentGraph: (id: number) => get<GraphData>(`/documents/${id}/graph`),
  suggestCategory: (fileName: string, text?: string) => get<CategorySuggestion[]>(`/documents/intelligence/suggest-category`, { file_name: fileName, text }),
  suggestTags: (text: string) => get<TagSuggestion[]>(`/documents/intelligence/suggest-tags`, { text }),
  searchSimilarByText: (text: string, excludeId?: number, limit?: number) => get<SimilarDocument[]>(`/documents/intelligence/search-similar`, { text, exclude_id: excludeId, limit }),
}

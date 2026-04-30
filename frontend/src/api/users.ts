import { get, post, put, del } from './index'
import type { PaginatedResponse } from './documents'

export interface UserItem {
  id: number
  username: string
  real_name: string
  email: string | null
  phone: string | null
  department_id: number | null
  department_name: string | null
  avatar_url: string | null
  status: string
  roles: { id: number; role_name: string; role_code: string }[]
  created_at: string
  updated_at: string
}

export interface RoleItem {
  id: number
  role_name: string
  role_code: string
  description: string | null
}

export interface DepartmentItem {
  id: number
  name: string
  code: string
  parent_id: number | null
  children_count: number
  created_at: string
}

export interface DocumentCategoryItem {
  id: number
  name: string
  code: string
  description: string | null
  sort_order: number
  is_system: boolean
  created_at: string | null
  updated_at: string | null
}

export interface TagItem {
  id: number
  name: string
  color: string
  created_at: string | null
  updated_at: string | null
}

export const usersApi = {
  getList: (params?: Record<string, any>) => get<PaginatedResponse<UserItem>>('/users', params),
  create: (data: Record<string, any>) => post<UserItem>('/users', data),
  getDetail: (id: number) => get<UserItem>(`/users/${id}`),
  update: (id: number, data: Record<string, any>) => put<UserItem>(`/users/${id}`, data),
  delete: (id: number) => del(`/users/${id}`),
  changePassword: (id: number, data: { old_password: string; new_password: string }) => put(`/users/${id}/password`, data),
  getRoles: () => get<RoleItem[]>('/users/roles'),
  createRole: (data: Record<string, any>) => post<RoleItem>('/users/roles', data),
  updateRole: (id: number, data: Record<string, any>) => put(`/users/roles/${id}`, data),
  deleteRole: (id: number) => del(`/users/roles/${id}`),
  getDepartments: () => get<DepartmentItem[]>('/users/departments'),
  getDepartmentTree: () => get<DepartmentItem[]>('/users/departments/tree'),
  createDepartment: (data: Record<string, any>) => post<DepartmentItem>('/users/departments', data),
  updateDepartment: (id: number, data: Record<string, any>) => put(`/users/departments/${id}`, data),
  deleteDepartment: (id: number) => del(`/users/departments/${id}`),
  getDocumentCategories: () => get<DocumentCategoryItem[]>('/users/document-categories'),
  createDocumentCategory: (data: Record<string, any>) => post<DocumentCategoryItem>('/users/document-categories', data),
  updateDocumentCategory: (id: number, data: Record<string, any>) => put(`/users/document-categories/${id}`, data),
  deleteDocumentCategory: (id: number) => del(`/users/document-categories/${id}`),
  getTags: () => get<TagItem[]>('/users/tags'),
  createTag: (data: Record<string, any>) => post<TagItem>('/users/tags', data),
  updateTag: (id: number, data: Record<string, any>) => put(`/users/tags/${id}`, data),
  deleteTag: (id: number) => del(`/users/tags/${id}`),
}

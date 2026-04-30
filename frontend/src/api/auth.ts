import { get, post } from './index'

export interface LoginRequest {
  username: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  expires_in: number
}

export interface UserInfo {
  id: number
  username: string
  real_name: string
  email: string | null
  department_id: number | null
  department_name: string | null
  roles: { id: number; role_name: string; role_code: string }[]
  avatar_url: string | null
}

export interface ProvidersResponse {
  providers: (string | { name: string; type: string })[]
}

export const authApi = {
  login: (data: LoginRequest) => post<TokenResponse>('/auth/login', data),
  ldapLogin: (data: LoginRequest) => post<TokenResponse>('/auth/ldap/login', data),
  logout: () => post('/auth/logout'),
  getMe: () => get<UserInfo>('/auth/me'),
  getProviders: () => get<ProvidersResponse>('/auth/providers'),
  getOAuth2AuthorizeUrl: () => '/api/v1/auth/oauth2/authorize',
}

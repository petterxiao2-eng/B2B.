import type { Project, Company, Contact, DashboardStats, SearchTask, DraftMessage } from '../types';

const API_BASE = '/api';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${url}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Request failed');
  }
  return response.json();
}

// Dashboard
export const dashboardApi = {
  getStats: () => request<DashboardStats>('/dashboard/stats'),
  getRecentActivity: () => request<{ activities: any[] }>('/dashboard/recent-activity'),
};

// Projects
export const projectsApi = {
  list: (status?: string) => request<{ projects: Project[]; total: number }>(
    `/projects${status ? `?status=${status}` : ''}`
  ),
  get: (id: string) => request<Project>(`/projects/${id}`),
  create: (data: Partial<Project>) => request<Project>('/projects', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  update: (id: string, data: Partial<Project>) => request<Project>(`/projects/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  }),
  delete: (id: string) => request<{ message: string }>(`/projects/${id}`, { method: 'DELETE' }),
};

// Companies
export const companiesApi = {
  list: (params: Record<string, string | number | undefined>) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => { if (v !== undefined) query.set(k, String(v)); });
    return request<{ companies: Company[]; total: number; page: number; page_size: number }>(
      `/companies?${query.toString()}`
    );
  },
  get: (id: string) => request<Company>(`/companies/${id}`),
  create: (data: Partial<Company>) => request<Company>('/companies', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  update: (id: string, data: Partial<Company>) => request<Company>(`/companies/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  }),
  delete: (id: string) => request<{ message: string }>(`/companies/${id}`, { method: 'DELETE' }),
  getContacts: (id: string) => request<{ contacts: Contact[] }>(`/companies/${id}/contacts`),
  exportCSV: (projectId: string, grade?: string) => {
    const url = `/companies/export/csv?project_id=${projectId}${grade ? `&grade=${grade}` : ''}`;
    window.open(`${API_BASE}${url}`, '_blank');
  },
  batchScore: (projectId: string) => request<{ message: string; scored: number }>(
    `/companies/batch-score?project_id=${projectId}`, { method: 'POST' }
  ),
  backgroundCheck: (id: string) => request<Record<string, unknown>>(
    `/companies/${id}/background-check`, { method: 'POST' }
  ),
  researchContacts: (id: string) => request<{ contacts_found: number; contacts_saved: number }>(
    `/companies/${id}/research-contacts`, { method: 'POST' }
  ),
};

// Contacts
export const contactsApi = {
  list: (params: Record<string, string | undefined>) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => { if (v) query.set(k, v); });
    return request<{ contacts: Contact[]; total: number }>(`/contacts?${query.toString()}`);
  },
  get: (id: string) => request<Contact>(`/contacts/${id}`),
  create: (data: Partial<Contact>) => request<Contact>('/contacts', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  update: (id: string, data: Partial<Contact>) => request<Contact>(`/contacts/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  }),
};

// Tasks
export const tasksApi = {
  list: (params: Record<string, string | undefined>) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => { if (v) query.set(k, v); });
    return request<{ tasks: SearchTask[] }>(`/tasks?${query.toString()}`);
  },
  triggerSearch: (projectId: string) => request<{ message: string; task_id: string }>(
    `/tasks/search?project_id=${projectId}`, { method: 'POST' }
  ),
  getQueueStats: () => request<{ total: number; by_status: Record<string, number> }>('/tasks/queue/stats'),
  getScheduled: () => request<{ jobs: any[] }>('/tasks/scheduled'),
  getProxyStatus: () => request<{
    summary: { total: number; healthy: number; degraded: number; avg_latency_ms: number; health_rate: number };
    by_region: { region: string; country: string; total: number; healthy: number }[];
    proxies: any[];
  }>('/tasks/proxy/status'),
};

// Drafts
export const draftsApi = {
  list: (params: Record<string, string | undefined>) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => { if (v) query.set(k, v); });
    return request<{ drafts: DraftMessage[] }>(`/drafts?${query.toString()}`);
  },
  generate: (companyId: string, contactId?: string, channel: string = 'email') =>
    request<DraftMessage>(`/drafts/generate?company_id=${companyId}&channel=${channel}${contactId ? `&contact_id=${contactId}` : ''}`, {
      method: 'POST',
    }),
  update: (id: string, data: { body?: string; subject?: string; status?: string }) =>
    request<{ message: string }>(`/drafts/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  delete: (id: string) => request<{ message: string }>(`/drafts/${id}`, { method: 'DELETE' }),
};

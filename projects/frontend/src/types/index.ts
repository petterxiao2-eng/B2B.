export interface Project {
  id: string;
  name: string;
  product_name: string;
  product_name_en?: string;
  product_description?: string;
  target_markets?: string[];
  priority_customer_types?: string[];
  delivery_mode?: string;
  key_advantages?: string;
  target_quantity: number;
  status: string;
  last_run_at?: string;
  created_at: string;
  updated_at: string;
  total_customers: number;
  a_grade_customers: number;
}

export interface Company {
  id: string;
  project_id: string;
  company_name: string;
  website?: string;
  country?: string;
  state_province?: string;
  city?: string;
  customer_type?: string;
  customer_pool?: string;
  main_business?: string;
  related_products?: string;
  product_match_evidence?: string;
  procurement_capability?: string;
  inventory_channel_capability?: string;
  score: number;
  score_details?: Record<string, number>;
  grade?: string;
  discovery_path?: string;
  source_keywords?: string;
  source_url_1?: string;
  source_url_2?: string;
  collected_at: string;
  suggested_approach?: string;
  items_to_verify?: string;
  review_status: string;
  background_report?: Record<string, any>;
  whatsapp_numbers?: string[];
  whatsapp_group_links?: string[];
  customs_data?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface Contact {
  id: string;
  company_id: string;
  project_id: string;
  company_name?: string;
  full_name?: string;
  job_title?: string;
  decision_role?: string;
  contact_grade?: string;
  personal_email?: string;
  email_status?: string;
  company_email?: string;
  personal_phone?: string;
  company_phone?: string;
  linkedin_personal?: string;
  linkedin_company?: string;
  identity_source_url?: string;
  contact_source_url?: string;
  collected_at: string;
  employment_status: string;
  suggested_channel?: string;
  research_notes?: string;
  review_status: string;
  created_at: string;
  updated_at: string;
}

export interface SearchTask {
  id: string;
  project_id: string;
  task_type: string;
  params?: Record<string, any>;
  status: string;
  priority: number;
  retry_count: number;
  error_message?: string;
  started_at?: string;
  completed_at?: string;
  created_at: string;
}

export interface DraftMessage {
  id: string;
  company_id: string;
  contact_id?: string;
  project_id: string;
  channel: string;
  subject?: string;
  body: string;
  content_breakdown?: Record<string, any>;
  status: string;
  created_at: string;
}

export interface DashboardStats {
  projects: { total: number; active: number };
  companies: {
    total: number;
    by_grade: { grade: string; count: number; label: string }[];
    by_country: { country: string; count: number }[];
  };
  contacts: { total: number; gold: number; silver: number; bronze: number };
  tasks: { pending: number; running: number };
  drafts: { pending_review: number };
}

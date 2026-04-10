export type TaskStatus = "todo" | "in_progress" | "done";
export type TaskPriority = "low" | "medium" | "high";

export type Theme = "light" | "dark";

export interface User {
  id: string;
  name: string;
  email: string;
  theme: Theme;
  created_at: string;
}

export interface Project {
  id: string;
  name: string;
  description: string | null;
  owner_id: string;
  created_at: string;
}

export interface Task {
  id: string;
  title: string;
  description: string | null;
  status: TaskStatus;
  priority: TaskPriority;
  project_id: string;
  assignee_id: string | null;
  due_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface ProjectStats {
  by_status: Record<TaskStatus, number>;
  by_assignee: Record<string, { name: string; count: number } | number>;
}

/** Normalised API error shape for UI display. */
export interface ApiError {
  status: number;
  data:
    | string
    | {
        error?: string;
        fields?: Record<string, string>;
        detail?: string | { error?: string; fields?: Record<string, string> };
      };
}

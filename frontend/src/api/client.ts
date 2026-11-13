import axios from 'axios';
import type {
  AuthStatusResponse,
  CourseItem,
  GradebookResponse,
  ReportCatalogItem,
  ReportData,
} from '../types';

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
});

export const authApi = {
  getStatus: async (): Promise<AuthStatusResponse> => (await api.get('/auth/status')).data,
  getGoogleUrl: async (): Promise<{ url: string }> => (await api.get('/auth/google/url')).data,
  disconnectGoogle: async () => (await api.post('/auth/google/disconnect')).data,
  loginCotemig: async (username: string, password: string) =>
    (await api.post('/auth/cotemig/login', { username, password })).data,
  logoutCotemig: async () => (await api.post('/auth/cotemig/logout')).data,
};

export const syncApi = {
  listCourses: async (): Promise<CourseItem[]> => (await api.get('/courses')).data,
  listExternalSources: async () => (await api.get('/sync/courses/external')).data,
  createMapping: async (payload: {
    classroom_course_id?: string | null;
    cotemig_class_id?: string | null;
    name: string;
    section?: string | null;
    term_period?: string;
    min_passing_grade?: number;
  }) => (await api.post('/courses/mapping', payload)).data,
  updateMapping: async (id: number, payload: Record<string, unknown>) =>
    (await api.put(`/courses/${id}`, payload)).data,
  listStudents: async (courseId: number) => (await api.get(`/courses/${courseId}/students`)).data,
  linkStudent: async (
    courseId: number,
    payload: { student_map_id: number; cotemig_ra?: string | null; status_cotemig?: string }
  ) => (await api.post(`/courses/${courseId}/students/link`, payload)).data,
  syncCourse: async (courseId: number) => (await api.post(`/sync/course/${courseId}`)).data,
  syncAll: async () => (await api.post('/sync/all')).data,
  seedDemo: async () => (await api.post('/sync/demo-seed')).data,
  getHistory: async () => (await api.get('/sync/history')).data,
};

export const rulesApi = {
  getGradebook: async (courseId: number): Promise<GradebookResponse> =>
    (await api.get(`/courses/${courseId}/gradebook`)).data,
  createTheme: async (
    courseId: number,
    payload: { title: string; max_points_cap: number | null; rounding_rule: string; order_index: number }
  ) => (await api.post(`/courses/${courseId}/themes`, payload)).data,
  updateRules: async (
    courseId: number,
    payload: {
      min_passing_grade?: number;
      use_draft_grades?: boolean;
      themes: {
        id: number | null;
        title: string;
        max_points_cap: number | null;
        rounding_rule: string;
        order_index: number;
      }[];
      activities: {
        id: number;
        theme_id: number | null;
        custom_points_weight: number;
        include_in_calc: boolean;
      }[];
    }
  ): Promise<GradebookResponse> => (await api.put(`/courses/${courseId}/rules`, payload)).data,
};

export const reportsApi = {
  getCatalog: async (): Promise<ReportCatalogItem[]> => (await api.get('/reports/catalog')).data,
  getReport: async (code: string, courseMapId?: number): Promise<ReportData> =>
    (
      await api.get(`/reports/${code}`, {
        params: courseMapId ? { course_map_id: courseMapId } : undefined,
      })
    ).data,
  getExportUrl: (code: string, format: 'xlsx' | 'csv' | 'pdf', courseMapId?: number) => {
    const params = new URLSearchParams({ format });
    if (courseMapId) params.set('course_map_id', String(courseMapId));
    return `/api/reports/${code}/export?${params.toString()}`;
  },
};


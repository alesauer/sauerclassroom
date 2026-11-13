export interface PlatformAuthStatus {
  connected: boolean;
  status: string;
  account: string | null;
  mode: string | null;
  details: string | null;
}

export interface AuthStatusResponse {
  google_classroom: PlatformAuthStatus;
  cotemig_portal: PlatformAuthStatus;
}

export interface CourseItem {
  id: number;
  classroom_course_id: string | null;
  cotemig_class_id: string | null;
  name: string;
  section: string | null;
  term_period: string;
  min_passing_grade: number;
  use_draft_grades: boolean;
  last_sync_at: string | null;
  students_count: number;
  activities_count: number;
}

export interface ThemeItem {
  id: number | null;
  title: string;
  max_points_cap: number | null;
  rounding_rule: string;
  order_index: number;
  raw_possible: number;
  effective_possible: number;
}

export interface ActivityItem {
  id: number;
  theme_id: number | null;
  title: string;
  classroom_work_id: string;
  due_date: string | null;
  classroom_max_points: number;
  custom_points_weight: number;
  include_in_calc: boolean;
  work_type: string;
}

export interface ActivityCell {
  activity_id: number;
  state: string;
  is_late: boolean;
  has_attachments: boolean;
  assigned_grade: number | null;
  draft_grade: number | null;
  calculated_points: number;
  include_in_calc: boolean;
}

export interface ThemeScore {
  theme_id: number | null;
  title: string;
  raw_sum: number;
  final_points: number;
  possible_points: number;
}

export interface StudentGradeRow {
  student_map_id: number;
  full_name: string;
  email: string | null;
  cotemig_ra: string | null;
  classroom_user_id: string | null;
  status_cotemig: string;
  match_method: string;
  theme_scores: Record<string, ThemeScore>;
  activity_cells: Record<string, ActivityCell>;
  total_points: number;
  total_possible: number;
  percentage: number;
  submission_rate: number;
  delivered_count: number;
  pending_count: number;
  late_count: number;
  no_attachment_count: number;
  risk_status: 'APROVADO' | 'ATENCAO' | 'RISCO';
  cotemig_official_grade: number | null;
  grade_divergence: number | null;
}

export interface GradebookResponse {
  course: {
    id: number;
    name: string;
    section: string | null;
    term_period: string;
    classroom_course_id: string | null;
    cotemig_class_id: string | null;
    min_passing_grade: number;
    use_draft_grades: boolean;
    last_sync_at: string | null;
    total_possible_points: number;
  };
  themes: ThemeItem[];
  activities: ActivityItem[];
  students: StudentGradeRow[];
}

export interface ReportCatalogItem {
  code: string;
  category: string;
  title: string;
  description: string;
}

export interface ReportData {
  code: string;
  title: string;
  category: string;
  description: string;
  course_name: string | null;
  generated_at: string;
  columns: { key: string; label: string }[];
  rows: Record<string, unknown>[];
  summary: Record<string, unknown>;
  chart_data: Record<string, unknown>[];
}


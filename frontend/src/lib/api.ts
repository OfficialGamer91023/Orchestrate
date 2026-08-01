import axios from "axios";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_TOKEN = process.env.NEXT_PUBLIC_API_TOKEN || "dev-token";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
    Authorization: `Bearer ${API_TOKEN}`,
  },
  timeout: 600000, // 10 minutes for batch eval
});

// ---- Types ----

export interface LogEntry {
  message_id: string;
  user_id: string;
  conversation_type: string;
  sender_user_id: string | null;
  group_id: string | null;
  business_id: string | null;
  message_text: string | null;
  media_type: string | null;
  audio_transcript: string | null;
  routing_decision: string | null;
  message_type: string | null;
  routing_reasoning: string | null;
  confidence: number | null;
  evidence_message_ids: string | null;
  processing_time_ms: number;
  route_method: string | null;
  processed_at: string | null;
}

export interface LogsResponse {
  total: number;
  page: number;
  limit: number;
  items: LogEntry[];
}

export interface ClassMetrics {
  precision: number;
  recall: number;
  f1: number;
  support: number;
}

export interface BatchEvalResponse {
  total_processed: number;
  accuracy: number;
  macro_f1: number;
  notify_fpr: number;
  class_metrics: Record<string, ClassMetrics>;
}

export interface DashboardStats {
  total_processed: number;
  overall_accuracy: number | null;
  avg_processing_time_ms: number;
  decision_distribution: Record<string, number>;
}

export interface HealthResponse {
  status: string;
  version: string;
  dataset_loaded: boolean;
  messages_count: number;
}

// ---- API Functions ----

export async function fetchDashboardStats(): Promise<DashboardStats> {
  const { data } = await api.get<DashboardStats>("/api/v1/dashboard-stats");
  return data;
}

export async function fetchLogs(
  page: number = 1,
  limit: number = 50,
  decisionFilter?: string
): Promise<LogsResponse> {
  const params: Record<string, string | number> = { page, limit };
  if (decisionFilter) params.decision_filter = decisionFilter;
  const { data } = await api.get<LogsResponse>("/api/v1/logs", { params });
  return data;
}

export async function runBatchEval(
  forceRecalculate: boolean = false
): Promise<BatchEvalResponse> {
  const { data } = await api.post<BatchEvalResponse>("/api/v1/batch-eval", null, {
    params: { force_recalculate: forceRecalculate },
  });
  return data;
}

export async function healthCheck(): Promise<HealthResponse> {
  const { data } = await api.get<HealthResponse>("/health");
  return data;
}

export default api;

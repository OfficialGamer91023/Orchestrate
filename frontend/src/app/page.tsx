"use client";

import { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import {
  Activity,
  Zap,
  Clock,
  TrendingUp,
  AlertTriangle,
  Play,
} from "lucide-react";
import { fetchDashboardStats, runBatchEval } from "@/lib/api";
import type { DashboardStats } from "@/lib/api";

import { useEvalStore } from "@/lib/store";

const DECISION_COLORS: Record<string, string> = {
  notify: "#22c55e",
  digest: "#eab308",
  mute: "#ef4444",
};

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const { isRunning: evalRunning, setIsRunning: setEvalRunning, setResult: setEvalResult } = useEvalStore();
  const [error, setError] = useState<string | null>(null);

  const loadStats = async () => {
    try {
      setLoading(true);
      const data = await fetchDashboardStats();
      setStats(data);
      setError(null);
    } catch {
      setError("Failed to connect to backend. Please check server status.");
    } finally {
      setLoading(false);
    }
  };

  const handleRunEval = async () => {
    try {
      setEvalRunning(true);
      const data = await runBatchEval(true);
      setEvalResult(data);
      await loadStats();
    } catch {
      setError("Batch evaluation failed. Check backend logs.");
    } finally {
      setEvalRunning(false);
    }
  };



  useEffect(() => {
    loadStats();
  }, []);

  // Chart data
  const chartData = stats
    ? Object.entries(stats.decision_distribution).map(([name, count]) => ({
        name: name.charAt(0).toUpperCase() + name.slice(1),
        count,
        key: name,
      }))
    : [];

  return (
    <div>
      {/* Page Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1
            className="text-2xl font-bold"
            style={{ color: "var(--text-primary)" }}
          >
            Dashboard Overview
          </h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
            Real-time routing metrics and system performance
          </p>
        </div>
        <button
          className="btn btn-primary"
          onClick={handleRunEval}
          disabled={evalRunning}
        >
          {evalRunning ? (
            <>
              <div className="animate-spin-slow">
                <Activity size={16} />
              </div>
              Processing...
            </>
          ) : (
            <>
              <Play size={16} />
              Run Evaluation Pipeline
            </>
          )}
        </button>
      </div>

      {/* Error Toast */}
      {error && (
        <div className="toast">
          <div className="flex items-center gap-3">
            <AlertTriangle size={18} style={{ color: "var(--accent-mute)" }} />
            <div>
              <p
                className="text-sm font-medium"
                style={{ color: "var(--text-primary)" }}
              >
                Connection Error
              </p>
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                {error}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        {/* Total Processed */}
        <div className="kpi-card">
          {loading ? (
            <KPISkeleton />
          ) : (
            <>
              <div className="flex items-center justify-between mb-4">
                <span
                  className="text-xs font-semibold uppercase tracking-wider"
                  style={{ color: "var(--text-muted)" }}
                >
                  Total Processed
                </span>
                <div
                  className="p-2 rounded-lg"
                  style={{ background: "rgba(56, 189, 248, 0.12)" }}
                >
                  <Zap size={18} style={{ color: "var(--text-accent)" }} />
                </div>
              </div>
              <p
                className="text-3xl font-bold"
                style={{ color: "var(--text-primary)" }}
              >
                {stats?.total_processed.toLocaleString() || "0"}
              </p>
              <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
                messages routed
              </p>
            </>
          )}
        </div>

        {/* Overall Accuracy */}
        <div className="kpi-card">
          {loading ? (
            <KPISkeleton />
          ) : (
            <>
              <div className="flex items-center justify-between mb-4">
                <span
                  className="text-xs font-semibold uppercase tracking-wider"
                  style={{ color: "var(--text-muted)" }}
                >
                  Overall Accuracy
                </span>
                <div
                  className="p-2 rounded-lg"
                  style={{ background: "rgba(34, 197, 94, 0.12)" }}
                >
                  <TrendingUp
                    size={18}
                    style={{ color: "var(--accent-notify)" }}
                  />
                </div>
              </div>
              <p
                className="text-3xl font-bold"
                style={{ color: "var(--text-primary)" }}
              >
                {stats?.overall_accuracy != null
                  ? `${(stats.overall_accuracy * 100).toFixed(1)}%`
                  : "—"}
              </p>
              <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
                vs golden labels
              </p>
            </>
          )}
        </div>

        {/* Avg Processing Time */}
        <div className="kpi-card">
          {loading ? (
            <KPISkeleton />
          ) : (
            <>
              <div className="flex items-center justify-between mb-4">
                <span
                  className="text-xs font-semibold uppercase tracking-wider"
                  style={{ color: "var(--text-muted)" }}
                >
                  Avg Processing Time
                </span>
                <div
                  className="p-2 rounded-lg"
                  style={{ background: "rgba(234, 179, 8, 0.12)" }}
                >
                  <Clock
                    size={18}
                    style={{ color: "var(--accent-digest)" }}
                  />
                </div>
              </div>
              <p
                className="text-3xl font-bold"
                style={{ color: "var(--text-primary)" }}
              >
                {stats?.avg_processing_time_ms
                  ? `${stats.avg_processing_time_ms.toFixed(0)}ms`
                  : "—"}
              </p>
              <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
                per message
              </p>
            </>
          )}
        </div>
      </div>

      {/* Chart */}
      <div className="card">
        <h2
          className="text-sm font-semibold uppercase tracking-wider mb-6"
          style={{ color: "var(--text-muted)" }}
        >
          Decision Distribution
        </h2>
        {loading ? (
          <div className="skeleton" style={{ height: 300 }} />
        ) : chartData.length === 0 ? (
          <EmptyState onRun={handleRunEval} running={evalRunning} />
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData} barCategoryGap="30%">
              <XAxis
                dataKey="name"
                tick={{ fill: "var(--text-muted)", fontSize: 13 }}
                axisLine={{ stroke: "var(--border-color)" }}
                tickLine={false}
              />
              <YAxis
                tick={{ fill: "var(--text-muted)", fontSize: 12 }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                contentStyle={{
                  background: "var(--bg-elevated)",
                  border: "1px solid var(--border-color)",
                  borderRadius: "var(--radius-md)",
                  color: "var(--text-primary)",
                  fontSize: 13,
                }}
                cursor={{ fill: "rgba(255,255,255,0.04)" }}
              />
              <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                {chartData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={DECISION_COLORS[entry.key] || "#64748b"}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}

function KPISkeleton() {
  return (
    <div className="space-y-3">
      <div className="skeleton" style={{ height: 16, width: 120 }} />
      <div className="skeleton" style={{ height: 36, width: 80 }} />
      <div className="skeleton" style={{ height: 12, width: 100 }} />
    </div>
  );
}

function EmptyState({
  onRun,
  running,
}: {
  onRun: () => void;
  running: boolean;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16">
      <div
        className="mb-4 p-4 rounded-full"
        style={{ background: "var(--bg-hover)" }}
      >
        <Activity size={32} style={{ color: "var(--text-muted)" }} />
      </div>
      <p
        className="text-sm font-medium mb-1"
        style={{ color: "var(--text-primary)" }}
      >
        No messages processed yet
      </p>
      <p
        className="text-xs mb-4"
        style={{ color: "var(--text-muted)" }}
      >
        Run the evaluation pipeline to start routing messages
      </p>
      <button
        className="btn btn-primary"
        onClick={onRun}
        disabled={running}
      >
        <Play size={14} />
        {running ? "Running..." : "Run Evaluation Pipeline"}
      </button>
    </div>
  );
}

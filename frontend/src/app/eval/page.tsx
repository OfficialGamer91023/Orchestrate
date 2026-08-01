"use client";

import { useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Legend,
} from "recharts";
import {
  Play,
  Activity,
  Target,
  AlertTriangle,
  CheckCircle2,
  Shield,
} from "lucide-react";
import { runBatchEval } from "@/lib/api";
import type { BatchEvalResponse, ClassMetrics } from "@/lib/api";

const CLASS_COLORS: Record<string, string> = {
  notify: "#22c55e",
  digest: "#eab308",
  mute: "#ef4444",
};

export default function EvalPage() {
  const [result, setResult] = useState<BatchEvalResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRun = async (force: boolean = false) => {
    try {
      setLoading(true);
      setError(null);
      const data = await runBatchEval(force);
      setResult(data);
    } catch {
      setError("Evaluation failed. Is the backend running?");
    } finally {
      setLoading(false);
    }
  };

  // Build chart data from class metrics
  const metricsBarData = result
    ? Object.entries(result.class_metrics).map(([cls, m]) => ({
        name: cls.charAt(0).toUpperCase() + cls.slice(1),
        key: cls,
        Precision: parseFloat((m.precision * 100).toFixed(1)),
        Recall: parseFloat((m.recall * 100).toFixed(1)),
        F1: parseFloat((m.f1 * 100).toFixed(1)),
      }))
    : [];

  const radarData = result
    ? Object.entries(result.class_metrics).flatMap(([cls, m]) => [
        { metric: `${cls} P`, value: m.precision * 100, cls },
        { metric: `${cls} R`, value: m.recall * 100, cls },
        { metric: `${cls} F1`, value: m.f1 * 100, cls },
      ])
    : [];

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1
            className="text-2xl font-bold"
            style={{ color: "var(--text-primary)" }}
          >
            Evaluation Benchmark
          </h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
            Performance metrics against golden evaluation dataset
          </p>
        </div>
        <div className="flex gap-3">
          <button
            className="btn btn-ghost"
            onClick={() => handleRun(false)}
            disabled={loading}
          >
            {loading ? "Running..." : "Use Cached"}
          </button>
          <button
            className="btn btn-primary"
            onClick={() => handleRun(true)}
            disabled={loading}
          >
            {loading ? (
              <>
                <div className="animate-spin-slow">
                  <Activity size={16} />
                </div>
                Processing...
              </>
            ) : (
              <>
                <Play size={16} />
                Run Fresh Evaluation
              </>
            )}
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div
          className="card mb-6 flex items-center gap-3"
          style={{ borderColor: "var(--accent-mute)" }}
        >
          <AlertTriangle size={18} style={{ color: "var(--accent-mute)" }} />
          <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
            {error}
          </p>
        </div>
      )}

      {!result && !loading && (
        <div className="flex flex-col items-center justify-center py-24">
          <div
            className="mb-4 p-5 rounded-full"
            style={{ background: "var(--bg-hover)" }}
          >
            <Target size={40} style={{ color: "var(--text-muted)" }} />
          </div>
          <p
            className="text-lg font-medium mb-2"
            style={{ color: "var(--text-primary)" }}
          >
            Ready to evaluate
          </p>
          <p
            className="text-sm mb-6 max-w-md text-center"
            style={{ color: "var(--text-muted)" }}
          >
            Run the evaluation pipeline to process all messages and compare
            predictions against golden labels from sample_messages.csv
          </p>
          <button className="btn btn-primary" onClick={() => handleRun(true)}>
            <Play size={16} />
            Start Evaluation
          </button>
        </div>
      )}

      {loading && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="kpi-card">
              <div className="space-y-3">
                <div className="skeleton" style={{ height: 16, width: 100 }} />
                <div className="skeleton" style={{ height: 36, width: 80 }} />
              </div>
            </div>
          ))}
        </div>
      )}

      {result && (
        <>
          {/* Summary KPIs */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            <div className="kpi-card">
              <div className="flex items-center justify-between mb-3">
                <span
                  className="text-xs font-semibold uppercase tracking-wider"
                  style={{ color: "var(--text-muted)" }}
                >
                  Total Processed
                </span>
                <Activity size={16} style={{ color: "var(--text-accent)" }} />
              </div>
              <p
                className="text-2xl font-bold"
                style={{ color: "var(--text-primary)" }}
              >
                {result.total_processed}
              </p>
            </div>

            <div className="kpi-card">
              <div className="flex items-center justify-between mb-3">
                <span
                  className="text-xs font-semibold uppercase tracking-wider"
                  style={{ color: "var(--text-muted)" }}
                >
                  Accuracy
                </span>
                <CheckCircle2
                  size={16}
                  style={{ color: "var(--accent-notify)" }}
                />
              </div>
              <p
                className="text-2xl font-bold"
                style={{ color: "var(--accent-notify)" }}
              >
                {(result.accuracy * 100).toFixed(1)}%
              </p>
            </div>

            <div className="kpi-card">
              <div className="flex items-center justify-between mb-3">
                <span
                  className="text-xs font-semibold uppercase tracking-wider"
                  style={{ color: "var(--text-muted)" }}
                >
                  Macro F1
                </span>
                <Target size={16} style={{ color: "var(--accent-digest)" }} />
              </div>
              <p
                className="text-2xl font-bold"
                style={{ color: "var(--accent-digest)" }}
              >
                {(result.macro_f1 * 100).toFixed(1)}%
              </p>
            </div>

            <div className="kpi-card">
              <div className="flex items-center justify-between mb-3">
                <span
                  className="text-xs font-semibold uppercase tracking-wider"
                  style={{ color: "var(--text-muted)" }}
                >
                  Notify FPR
                </span>
                <Shield size={16} style={{ color: "var(--accent-mute)" }} />
              </div>
              <p
                className="text-2xl font-bold"
                style={{
                  color:
                    result.notify_fpr < 0.1
                      ? "var(--accent-notify)"
                      : "var(--accent-mute)",
                }}
              >
                {(result.notify_fpr * 100).toFixed(1)}%
              </p>
              <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
                false positive rate
              </p>
            </div>
          </div>

          {/* Class Metrics Table */}
          <div className="card mb-8" style={{ padding: 0, overflow: "hidden" }}>
            <div className="px-6 py-4" style={{ borderBottom: "1px solid var(--border-color)" }}>
              <h2
                className="text-sm font-semibold uppercase tracking-wider"
                style={{ color: "var(--text-muted)" }}
              >
                Per-Class Performance
              </h2>
            </div>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Class</th>
                  <th>Precision</th>
                  <th>Recall</th>
                  <th>F1 Score</th>
                  <th>Support</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(result.class_metrics).map(([cls, m]) => (
                  <tr key={cls} style={{ cursor: "default" }}>
                    <td>
                      <span
                        className="inline-flex items-center gap-2 font-medium"
                        style={{ color: CLASS_COLORS[cls] || "var(--text-primary)" }}
                      >
                        <span
                          className="w-2 h-2 rounded-full"
                          style={{
                            background: CLASS_COLORS[cls] || "var(--text-muted)",
                          }}
                        />
                        {cls.charAt(0).toUpperCase() + cls.slice(1)}
                      </span>
                    </td>
                    <td>
                      <MetricBar value={m.precision} color={CLASS_COLORS[cls]} />
                    </td>
                    <td>
                      <MetricBar value={m.recall} color={CLASS_COLORS[cls]} />
                    </td>
                    <td>
                      <MetricBar value={m.f1} color={CLASS_COLORS[cls]} />
                    </td>
                    <td className="font-mono">{m.support}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Bar Chart */}
            <div className="card">
              <h2
                className="text-sm font-semibold uppercase tracking-wider mb-6"
                style={{ color: "var(--text-muted)" }}
              >
                Metrics Comparison
              </h2>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={metricsBarData} barCategoryGap="20%">
                  <XAxis
                    dataKey="name"
                    tick={{ fill: "var(--text-muted)", fontSize: 12 }}
                    axisLine={{ stroke: "var(--border-color)" }}
                    tickLine={false}
                  />
                  <YAxis
                    domain={[0, 100]}
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
                      fontSize: 12,
                    }}
                    formatter={(value: any) => [`${Number(value || 0).toFixed(1)}%`]}
                  />
                  <Legend
                    wrapperStyle={{ fontSize: 12, color: "var(--text-muted)" }}
                  />
                  <Bar dataKey="Precision" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="Recall" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="F1" fill="#06b6d4" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Radar Chart */}
            <div className="card">
              <h2
                className="text-sm font-semibold uppercase tracking-wider mb-6"
                style={{ color: "var(--text-muted)" }}
              >
                Performance Radar
              </h2>
              <ResponsiveContainer width="100%" height={280}>
                <RadarChart data={radarData}>
                  <PolarGrid stroke="var(--border-color)" />
                  <PolarAngleAxis
                    dataKey="metric"
                    tick={{ fill: "var(--text-muted)", fontSize: 10 }}
                  />
                  <PolarRadiusAxis
                    domain={[0, 100]}
                    tick={{ fill: "var(--text-muted)", fontSize: 10 }}
                  />
                  <Radar
                    name="Score"
                    dataKey="value"
                    stroke="#38bdf8"
                    fill="#38bdf8"
                    fillOpacity={0.2}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function MetricBar({ value, color }: { value: number; color?: string }) {
  return (
    <div className="flex items-center gap-2">
      <div
        className="flex-1 h-2 rounded-full overflow-hidden"
        style={{ background: "var(--bg-primary)", maxWidth: 100 }}
      >
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{
            width: `${(value * 100).toFixed(0)}%`,
            background: color || "var(--text-accent)",
          }}
        />
      </div>
      <span className="text-xs font-mono" style={{ color: "var(--text-primary)", minWidth: 44 }}>
        {(value * 100).toFixed(1)}%
      </span>
    </div>
  );
}

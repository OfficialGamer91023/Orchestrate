"use client";

import { useEffect, useState, useCallback } from "react";
import {
  Mic,
  Image as ImageIcon,
  ChevronLeft,
  ChevronRight,
  Search,
  Filter,
  Activity,
  Play,
} from "lucide-react";
import { fetchLogs, runBatchEval } from "@/lib/api";
import type { LogEntry, LogsResponse } from "@/lib/api";
import DecisionBadge from "@/components/shared/decision-badge";
import MessageSheet from "@/components/shared/message-sheet";

const FILTER_OPTIONS = [
  { value: "", label: "All" },
  { value: "notify", label: "Notify" },
  { value: "digest", label: "Digest" },
  { value: "mute", label: "Mute" },
];

export default function LogsPage() {
  const [logs, setLogs] = useState<LogsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [filter, setFilter] = useState("");
  const [selectedEntry, setSelectedEntry] = useState<LogEntry | null>(null);
  const [evalRunning, setEvalRunning] = useState(false);
  const limit = 25;

  const loadLogs = useCallback(async () => {
    try {
      setLoading(true);
      const data = await fetchLogs(page, limit, filter || undefined);
      setLogs(data);
    } catch {
      // Error handled by empty state
    } finally {
      setLoading(false);
    }
  }, [page, filter]);

  const handleRunEval = async () => {
    try {
      setEvalRunning(true);
      await runBatchEval(true);
      await loadLogs();
    } catch {
      // Handle error
    } finally {
      setEvalRunning(false);
    }
  };

  useEffect(() => {
    loadLogs();
  }, [loadLogs]);

  const totalPages = logs ? Math.ceil(logs.total / limit) : 0;

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1
            className="text-2xl font-bold"
            style={{ color: "var(--text-primary)" }}
          >
            Message Logs
          </h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
            Audit trail of every processed message
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Filter */}
          <div className="flex items-center gap-2">
            <Filter size={14} style={{ color: "var(--text-muted)" }} />
            <select
              value={filter}
              onChange={(e) => {
                setFilter(e.target.value);
                setPage(1);
              }}
              className="text-sm rounded-lg px-3 py-2 outline-none"
              style={{
                background: "var(--bg-elevated)",
                color: "var(--text-primary)",
                border: "1px solid var(--border-color)",
              }}
            >
              {FILTER_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        {loading ? (
          <TableSkeleton />
        ) : !logs || logs.items.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20">
            <div
              className="mb-4 p-4 rounded-full"
              style={{ background: "var(--bg-hover)" }}
            >
              <Search size={32} style={{ color: "var(--text-muted)" }} />
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
              onClick={handleRunEval}
              disabled={evalRunning}
            >
              {evalRunning ? (
                <>
                  <div className="animate-spin-slow">
                    <Activity size={14} />
                  </div>
                  Processing...
                </>
              ) : (
                <>
                  <Play size={14} />
                  Run Evaluation Pipeline
                </>
              )}
            </button>
          </div>
        ) : (
          <>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Message ID</th>
                  <th>Sender</th>
                  <th>Type</th>
                  <th>Media</th>
                  <th>Decision</th>
                  <th>Confidence</th>
                  <th>Processing</th>
                </tr>
              </thead>
              <tbody>
                {logs.items.map((entry) => (
                  <tr
                    key={entry.message_id}
                    onClick={() => setSelectedEntry(entry)}
                  >
                    <td className="font-mono text-xs">
                      {entry.processed_at
                        ? new Date(entry.processed_at).toLocaleTimeString()
                        : "—"}
                    </td>
                    <td>
                      <span
                        className="font-mono text-xs"
                        style={{ color: "var(--text-accent)" }}
                      >
                        {entry.message_id}
                      </span>
                    </td>
                    <td>{entry.sender_user_id || entry.business_id || "—"}</td>
                    <td>
                      <span
                        className="text-xs px-2 py-1 rounded"
                        style={{
                          background: "var(--bg-primary)",
                          color: "var(--text-secondary)",
                        }}
                      >
                        {entry.conversation_type}
                      </span>
                    </td>
                    <td>
                      <div className="flex gap-1">
                        {entry.media_type === "voice" && (
                          <Mic
                            size={14}
                            style={{ color: "var(--accent-notify)" }}
                          />
                        )}
                        {entry.media_type === "image" && (
                          <ImageIcon
                            size={14}
                            style={{ color: "var(--accent-digest)" }}
                          />
                        )}
                        {!entry.media_type && (
                          <span style={{ color: "var(--text-muted)" }}>—</span>
                        )}
                      </div>
                    </td>
                    <td>
                      {entry.routing_decision ? (
                        <DecisionBadge decision={entry.routing_decision} />
                      ) : (
                        <span style={{ color: "var(--text-muted)" }}>—</span>
                      )}
                    </td>
                    <td>
                      {entry.confidence != null ? (
                        <span className="font-mono text-xs">
                          {(entry.confidence * 100).toFixed(0)}%
                        </span>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td>
                      <span className="font-mono text-xs">
                        {entry.processing_time_ms}ms
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Pagination */}
            {totalPages > 1 && (
              <div
                className="flex items-center justify-between px-4 py-3"
                style={{
                  borderTop: "1px solid var(--border-color)",
                }}
              >
                <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                  Showing {(page - 1) * limit + 1}–
                  {Math.min(page * limit, logs.total)} of {logs.total}
                </p>
                <div className="flex items-center gap-2">
                  <button
                    className="btn btn-ghost"
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                    style={{ padding: "0.375rem 0.75rem" }}
                  >
                    <ChevronLeft size={14} />
                  </button>
                  <span
                    className="text-sm font-mono"
                    style={{ color: "var(--text-secondary)" }}
                  >
                    {page} / {totalPages}
                  </span>
                  <button
                    className="btn btn-ghost"
                    onClick={() =>
                      setPage((p) => Math.min(totalPages, p + 1))
                    }
                    disabled={page === totalPages}
                    style={{ padding: "0.375rem 0.75rem" }}
                  >
                    <ChevronRight size={14} />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Slide-Over Sheet */}
      {selectedEntry && (
        <MessageSheet
          entry={selectedEntry}
          onClose={() => setSelectedEntry(null)}
        />
      )}
    </div>
  );
}

function TableSkeleton() {
  return (
    <div className="p-4 space-y-3">
      {Array.from({ length: 10 }).map((_, i) => (
        <div key={i} className="flex gap-4 items-center">
          <div className="skeleton" style={{ height: 16, width: 80 }} />
          <div className="skeleton" style={{ height: 16, width: 70 }} />
          <div className="skeleton" style={{ height: 16, width: 60 }} />
          <div className="skeleton" style={{ height: 16, width: 60 }} />
          <div className="skeleton" style={{ height: 16, width: 24 }} />
          <div className="skeleton" style={{ height: 24, width: 70 }} />
          <div className="skeleton" style={{ height: 16, width: 40 }} />
          <div className="skeleton" style={{ height: 16, width: 50 }} />
        </div>
      ))}
    </div>
  );
}

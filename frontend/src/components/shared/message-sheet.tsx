"use client";

import { X, Mic, Image, Clock, User, MessageSquare } from "lucide-react";
import DecisionBadge from "./decision-badge";
import type { LogEntry } from "@/lib/api";

interface MessageSheetProps {
  entry: LogEntry;
  onClose: () => void;
}

export default function MessageSheet({ entry, onClose }: MessageSheetProps) {
  return (
    <>
      {/* Overlay */}
      <div className="sheet-overlay" onClick={onClose} />

      {/* Panel */}
      <div className="sheet-panel">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2
              className="text-lg font-semibold"
              style={{ color: "var(--text-primary)" }}
            >
              Message Details
            </h2>
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>
              {entry.message_id}
            </p>
          </div>
          <button
            onClick={onClose}
            className="btn-ghost p-2 rounded-lg"
            style={{
              background: "transparent",
              border: "1px solid var(--border-color)",
              cursor: "pointer",
              color: "var(--text-muted)",
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Decision */}
        <div className="card mb-4">
          <div className="flex items-center justify-between mb-3">
            <span
              className="text-xs font-semibold uppercase tracking-wider"
              style={{ color: "var(--text-muted)" }}
            >
              Routing Decision
            </span>
            <DecisionBadge decision={entry.routing_decision || "digest"} />
          </div>
          {entry.message_type && (
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                Type:
              </span>
              <span
                className="text-sm font-medium"
                style={{ color: "var(--text-primary)" }}
              >
                {entry.message_type}
              </span>
            </div>
          )}
          {entry.confidence != null && (
            <div className="flex items-center gap-2">
              <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                Confidence:
              </span>
              <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ background: "var(--bg-primary)" }}>
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${(entry.confidence * 100).toFixed(0)}%`,
                    background: `linear-gradient(90deg, #3b82f6, ${
                      entry.confidence > 0.8
                        ? "#22c55e"
                        : entry.confidence > 0.5
                        ? "#eab308"
                        : "#ef4444"
                    })`,
                  }}
                />
              </div>
              <span
                className="text-sm font-mono"
                style={{ color: "var(--text-primary)" }}
              >
                {(entry.confidence * 100).toFixed(0)}%
              </span>
            </div>
          )}
        </div>

        {/* Metadata */}
        <div className="card mb-4">
          <h3
            className="text-xs font-semibold uppercase tracking-wider mb-3"
            style={{ color: "var(--text-muted)" }}
          >
            Message Info
          </h3>
          <div className="grid grid-cols-2 gap-3">
            <InfoRow icon={User} label="User" value={entry.user_id} />
            <InfoRow
              icon={User}
              label="Sender"
              value={entry.sender_user_id || "—"}
            />
            <InfoRow
              icon={MessageSquare}
              label="Type"
              value={entry.conversation_type}
            />
            <InfoRow
              icon={Clock}
              label="Processing"
              value={`${entry.processing_time_ms}ms`}
            />
          </div>
        </div>

        {/* Original Text */}
        {entry.message_text && (
          <div className="card mb-4">
            <h3
              className="text-xs font-semibold uppercase tracking-wider mb-3"
              style={{ color: "var(--text-muted)" }}
            >
              Original Message
            </h3>
            <p className="text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
              {entry.message_text}
            </p>
          </div>
        )}

        {/* Audio Transcript */}
        {entry.audio_transcript && (
          <div className="card mb-4">
            <div className="flex items-center gap-2 mb-3">
              <Mic size={14} style={{ color: "var(--accent-notify)" }} />
              <h3
                className="text-xs font-semibold uppercase tracking-wider"
                style={{ color: "var(--text-muted)" }}
              >
                Audio Transcript
              </h3>
            </div>
            <blockquote
              className="text-sm italic pl-3"
              style={{
                color: "var(--text-secondary)",
                borderLeft: "3px solid var(--accent-notify)",
              }}
            >
              {entry.audio_transcript}
            </blockquote>
          </div>
        )}

        {/* Media indicator */}
        {entry.media_type && (
          <div className="card mb-4">
            <div className="flex items-center gap-2">
              {entry.media_type === "voice" ? (
                <Mic size={14} style={{ color: "var(--accent-digest)" }} />
              ) : (
                <Image size={14} style={{ color: "var(--accent-digest)" }} />
              )}
              <span className="text-sm" style={{ color: "var(--text-secondary)" }}>
                {entry.media_type === "voice" ? "Voice note" : "Image"} attached
              </span>
            </div>
          </div>
        )}

        {/* LLM Reasoning */}
        {entry.routing_reasoning && (
          <div className="card mb-4">
            <h3
              className="text-xs font-semibold uppercase tracking-wider mb-3"
              style={{ color: "var(--text-muted)" }}
            >
              LLM Reasoning
            </h3>
            <div
              className="text-sm p-3 rounded-lg font-mono leading-relaxed"
              style={{
                background: "var(--bg-primary)",
                color: "var(--text-secondary)",
                border: "1px solid var(--border-subtle)",
              }}
            >
              {entry.routing_reasoning}
            </div>
          </div>
        )}

        {/* Evidence */}
        {entry.evidence_message_ids &&
          entry.evidence_message_ids !== "none" && (
            <div className="card">
              <h3
                className="text-xs font-semibold uppercase tracking-wider mb-3"
                style={{ color: "var(--text-muted)" }}
              >
                Evidence Message IDs
              </h3>
              <div className="flex flex-wrap gap-2">
                {entry.evidence_message_ids.split(";").map((id) => (
                  <span
                    key={id}
                    className="text-xs px-2 py-1 rounded-md font-mono"
                    style={{
                      background: "var(--bg-primary)",
                      color: "var(--text-accent)",
                      border: "1px solid var(--border-color)",
                    }}
                  >
                    {id.trim()}
                  </span>
                ))}
              </div>
            </div>
          )}
      </div>
    </>
  );
}

function InfoRow({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center gap-2">
      <Icon size={14} style={{ color: "var(--text-muted)" }} />
      <div>
        <p className="text-xs" style={{ color: "var(--text-muted)" }}>
          {label}
        </p>
        <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
          {value}
        </p>
      </div>
    </div>
  );
}

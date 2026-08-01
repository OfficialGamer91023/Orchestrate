"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  MessageSquare,
  BarChart3,
  ChevronLeft,
  ChevronRight,
  Zap,
} from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  {
    href: "/",
    label: "Dashboard",
    icon: LayoutDashboard,
  },
  {
    href: "/logs",
    label: "Message Logs",
    icon: MessageSquare,
  },
  {
    href: "/eval",
    label: "Evaluation",
    icon: BarChart3,
  },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className={cn("sidebar", collapsed && "sidebar-collapsed")}
      style={{ width: collapsed ? 72 : 260 }}
    >
      {/* Logo */}
      <div
        className="flex items-center gap-3 px-5 py-5 border-b"
        style={{ borderColor: "var(--border-color)" }}
      >
        <div
          className="flex items-center justify-center rounded-lg"
          style={{
            width: 36,
            height: 36,
            background: "linear-gradient(135deg, #3b82f6, #8b5cf6)",
          }}
        >
          <Zap size={20} className="text-white" />
        </div>
        {!collapsed && (
          <div className="flex flex-col">
            <span
              className="text-sm font-bold"
              style={{ color: "var(--text-primary)" }}
            >
              Orchestrate
            </span>
            <span
              className="text-xs"
              style={{ color: "var(--text-muted)" }}
            >
              Message Router
            </span>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "sidebar-link",
                isActive && "sidebar-link-active"
              )}
              title={collapsed ? item.label : undefined}
            >
              <Icon size={20} />
              {!collapsed && <span>{item.label}</span>}
            </Link>
          );
        })}
      </nav>

      {/* Collapse Toggle */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="flex items-center justify-center py-4 border-t cursor-pointer"
        style={{
          borderColor: "var(--border-color)",
          color: "var(--text-muted)",
          background: "transparent",
          border: "none",
          borderTop: "1px solid var(--border-color)",
          width: "100%",
        }}
      >
        {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
      </button>
    </aside>
  );
}

"use client";

import { Bell, Clock, ShieldAlert } from "lucide-react";
import { cn } from "@/lib/utils";

interface DecisionBadgeProps {
  decision: string;
  className?: string;
}

const BADGE_CONFIG: Record<
  string,
  { icon: React.ElementType; className: string; label: string }
> = {
  notify: {
    icon: Bell,
    className: "badge-notify",
    label: "Notify",
  },
  digest: {
    icon: Clock,
    className: "badge-digest",
    label: "Digest",
  },
  mute: {
    icon: ShieldAlert,
    className: "badge-mute",
    label: "Mute",
  },
};

export default function DecisionBadge({
  decision,
  className,
}: DecisionBadgeProps) {
  const config = BADGE_CONFIG[decision] || BADGE_CONFIG.digest;
  const Icon = config.icon;

  return (
    <span className={cn("badge", config.className, className)}>
      <Icon size={12} />
      {config.label}
    </span>
  );
}

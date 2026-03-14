"use client";

import { Loader2, CheckCircle2, AlertCircle, Clock } from "lucide-react";
import { cn } from "@/lib/utils";
import { ScoreBadge } from "./score-badge";
import type { AreaResearch } from "@/types";

interface ResearchProgressProps {
  research: AreaResearch | undefined;
  compact?: boolean;
}

export function ResearchProgress({ research, compact }: ResearchProgressProps) {
  if (!research) return null;

  const { status, overall_score } = research;

  if (status === "queued") {
    return (
      <div
        className={cn(
          "flex items-center gap-1.5",
          compact ? "text-[10px]" : "text-xs"
        )}
      >
        <Clock className="h-3 w-3 text-muted-foreground animate-pulse" />
        <span className="text-muted-foreground">Waiting...</span>
      </div>
    );
  }

  if (status === "running") {
    return (
      <div className="space-y-1">
        <div
          className={cn(
            "flex items-center gap-1.5",
            compact ? "text-[10px]" : "text-xs"
          )}
        >
          <Loader2 className="h-3 w-3 text-teal-500 animate-spin" />
          <span className="text-teal-600">Researching...</span>
        </div>
        {!compact && (
          <div className="h-1 w-full rounded-full bg-muted overflow-hidden">
            <div className="h-full w-1/3 bg-teal-500 rounded-full animate-pulse" />
          </div>
        )}
      </div>
    );
  }

  if (status === "done" && overall_score != null) {
    return (
      <div
        className={cn(
          "flex items-center gap-1.5",
          compact ? "text-[10px]" : "text-xs"
        )}
      >
        <CheckCircle2 className="h-3 w-3 text-emerald-500" />
        <ScoreBadge score={overall_score} size="sm" />
      </div>
    );
  }

  if (status === "failed") {
    return (
      <div
        className={cn(
          "flex items-center gap-1.5",
          compact ? "text-[10px]" : "text-xs"
        )}
      >
        <AlertCircle className="h-3 w-3 text-red-500" />
        <span className="text-red-600">Error</span>
      </div>
    );
  }

  return null;
}

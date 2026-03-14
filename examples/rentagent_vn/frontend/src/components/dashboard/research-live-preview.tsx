"use client";

import { cn } from "@/lib/utils";

interface ResearchLivePreviewProps {
  browserUrl: string | null;
  currentDetail: string | null;
  className?: string;
}

export function ResearchLivePreview({
  browserUrl,
  currentDetail,
  className,
}: ResearchLivePreviewProps) {
  return (
    <div className={cn("space-y-2", className)}>
      {/* Step ticker with ping dot */}
      <div className="flex items-center gap-1.5">
        <span className="relative flex h-1.5 w-1.5">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-teal-400 opacity-75" />
          <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-teal-500" />
        </span>
        <span className="text-xs text-teal-700 dark:text-teal-400 truncate max-w-[200px]">
          {currentDetail || "Researching..."}
        </span>
      </div>

      {/* Live preview iframe or skeleton */}
      {browserUrl ? (
        <iframe
          src={browserUrl}
          className="w-full h-40 rounded-md border bg-white"
          sandbox="allow-same-origin allow-scripts"
          title="Live research preview"
        />
      ) : (
        <div className="w-full h-40 rounded-md border bg-muted/50 animate-pulse flex items-center justify-center">
          <span className="text-xs text-muted-foreground">
            Waiting for live preview...
          </span>
        </div>
      )}
    </div>
  );
}

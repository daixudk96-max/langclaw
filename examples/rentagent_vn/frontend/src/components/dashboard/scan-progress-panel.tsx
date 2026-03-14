"use client";

import { Check, Loader2, Globe } from "lucide-react";
import { useScanStreamStore } from "@/stores/scan-stream-store";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";

export function ScanProgressPanel() {
  const {
    status,
    steps,
    streamingUrls,
    activeUrl,
    listingsFound,
    setActiveUrl,
  } = useScanStreamStore();

  if (status === "idle") return null;

  const activeStreamUrl = activeUrl ? streamingUrls[activeUrl] : null;
  const urlList = Object.keys(streamingUrls);

  // Filter steps by the selected URL
  const filteredSteps = activeUrl
    ? steps.filter((step) => step.url === activeUrl)
    : steps;

  return (
    <Card className="mx-4 mb-4 border-blue-200 bg-blue-50/50 dark:border-blue-900 dark:bg-blue-950/20">
      <CardHeader className="py-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            {(status === "streaming" || status === "connecting") && (
              <Loader2 className="h-4 w-4 animate-spin" />
            )}
            {status === "complete" && (
              <Check className="h-4 w-4 text-green-600" />
            )}
            {status === "connecting" && "Connecting..."}
            {status === "streaming" && "Scanning..."}
            {status === "complete" && "Complete"}
            {status === "error" && "Error"}
          </CardTitle>
          {status === "complete" && (
            <Badge variant="secondary">{listingsFound} found</Badge>
          )}
        </div>

        {/* URL selector chips at top */}
        {urlList.length > 0 && (
          <div className="flex gap-1.5 mt-3 flex-wrap">
            {urlList.map((url) => (
              <Button
                key={url}
                size="sm"
                variant={url === activeUrl ? "default" : "outline"}
                className="text-xs h-7"
                onClick={() => setActiveUrl(url)}
              >
                <Globe className="h-3 w-3 mr-1.5" />
                {(() => {
                  try {
                    return new URL(url).hostname;
                  } catch {
                    return url;
                  }
                })()}
              </Button>
            ))}
          </div>
        )}
      </CardHeader>

      <CardContent className="py-0 pb-4">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Live preview iframe (left) */}
          <div className="relative">
            {activeStreamUrl ? (
              <iframe
                src={activeStreamUrl}
                className="w-full h-64 rounded border bg-white"
                sandbox="allow-same-origin allow-scripts"
                title="Live agent preview"
              />
            ) : (
              <div className="w-full h-64 rounded border bg-muted/50 flex items-center justify-center text-sm text-muted-foreground">
                {status === "streaming" || status === "connecting"
                  ? "Waiting for live preview..."
                  : "No preview"}
              </div>
            )}
          </div>

          {/* Progress steps filtered by URL (right) */}
          <ScrollArea className="h-64">
            <div className="space-y-1.5 pr-4">
              {filteredSteps.length === 0 &&
                (status === "connecting" || status === "streaming") && (
                  <div className="text-sm text-muted-foreground">
                    {activeUrl ? "Waiting for events from this source..." : "Waiting for events..."}
                  </div>
                )}
              {filteredSteps.map((step) => (
                <div key={step.id} className="flex items-start gap-2 text-sm">
                  {step.status === "running" ? (
                    <Loader2 className="h-3.5 w-3.5 mt-0.5 animate-spin text-blue-500 flex-shrink-0" />
                  ) : (
                    <Check className="h-3.5 w-3.5 mt-0.5 text-green-500 flex-shrink-0" />
                  )}
                  <span className="flex-1 text-muted-foreground">
                    {step.purpose}
                  </span>
                  {step.duration != null && (
                    <span className="text-xs text-muted-foreground tabular-nums">
                      {step.duration.toFixed(1)}s
                    </span>
                  )}
                </div>
              ))}
            </div>
          </ScrollArea>
        </div>
      </CardContent>
    </Card>
  );
}

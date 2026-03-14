"use client";

import { Loader2, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useActivityStore } from "@/stores/activity-store";
import { toast } from "sonner";

interface ScanControlsProps {
  campaignId: string;
}

export function ScanControls({ campaignId }: ScanControlsProps) {
  const { isScanning, triggerScan } = useActivityStore();

  const handleScan = async () => {
    try {
      await triggerScan(campaignId);
      toast.success("Scan started. Results will be ready in a few minutes.");
      // Data refresh is handled by the SSE stream completion in dashboard.tsx
    } catch {
      toast.error("Cannot scan right now. Try again later.");
    }
  };

  return (
    <Button
      onClick={handleScan}
      disabled={isScanning}
      variant={isScanning ? "secondary" : "default"}
      size="sm"
    >
      {isScanning ? (
        <>
          <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
          Scanning...
        </>
      ) : (
        <>
          <RefreshCw className="h-4 w-4 mr-1.5" />
          Scan now
        </>
      )}
    </Button>
  );
}

"use client";

import { useState, useEffect } from "react";
import { useCampaignStore } from "@/stores/campaign-store";
import { useActivityStore } from "@/stores/activity-store";
import { useScanStreamStore } from "@/stores/scan-stream-store";
import { useResearchStore } from "@/stores/research-store";
import { useCampaign } from "@/hooks/use-campaign";
import { useScanStream } from "@/hooks/use-scan-stream";
import { useResearchStream } from "@/hooks/use-research-stream";
import { TopBar } from "./top-bar";
import { StatsPanel } from "./stats-panel";
import { Pipeline } from "./pipeline";
import { ListingDetail } from "./listing-detail";
import { ScanControls } from "./scan-controls";
import { ScanProgressPanel } from "./scan-progress-panel";
import { ResearchActionBar } from "./research-action-bar";
import { ResearchConfigSheet } from "./research-config-sheet";
import { ChatPanel } from "@/components/chat/chat-panel";
import { ActivityFeed } from "@/components/activity/activity-feed";
import { useListingStore } from "@/stores/listing-store";

interface DashboardProps {
  campaignId: string;
}

export function Dashboard({ campaignId }: DashboardProps) {
  const { campaign, fetchStats } = useCampaignStore();
  const { selectedListing, selectListing, fetchListings } = useListingStore();
  const { isScanning, latestScan, fetchScans, fetchActivities } =
    useActivityStore();
  const scanStatus = useScanStreamStore((s) => s.status);
  const { fetchAllResearch, researching } = useResearchStore();
  const [chatOpen, setChatOpen] = useState(false);

  // Check if any research is active
  const hasActiveResearch = Object.values(researching).some(
    (r) => r.status === "queued" || r.status === "running"
  );

  // Load all campaign data + poll
  useCampaign(campaignId);

  // Connect SSE when scanning
  useScanStream(campaignId, isScanning && latestScan ? latestScan.id : null);

  // Connect research SSE when research is active
  useResearchStream(campaignId, hasActiveResearch);

  // Refetch data when scan completes
  useEffect(() => {
    if (scanStatus === "complete") {
      fetchListings(campaignId);
      fetchStats(campaignId);
      fetchScans(campaignId);
      fetchActivities(campaignId);
    }
  }, [
    scanStatus,
    campaignId,
    fetchListings,
    fetchStats,
    fetchScans,
    fetchActivities,
  ]);

  // Load research data on mount
  useEffect(() => {
    fetchAllResearch(campaignId);
  }, [campaignId, fetchAllResearch]);

  if (!campaign) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-pulse text-muted-foreground">
          Đang tải...
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen bg-background flex flex-col overflow-hidden">
      <TopBar campaign={campaign} onChatToggle={() => setChatOpen(!chatOpen)} />

      <div className="flex-1 flex min-h-0">
        {/* Main content */}
        <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
          <div className="flex-shrink-0 p-4 flex items-center justify-between">
            <StatsPanel />
            <ScanControls campaignId={campaignId} />
          </div>

          <ScanProgressPanel />

          <div className="flex-1 min-h-0 overflow-hidden px-4 pb-4">
            <Pipeline campaignId={campaignId} />
          </div>
        </div>
      </div>

      {/* Listing detail drawer */}
      {selectedListing && (
        <ListingDetail
          listing={selectedListing}
          campaignId={campaignId}
          onClose={() => selectListing(null)}
        />
      )}

      {/* Research selection action bar */}
      <ResearchActionBar />
      <ResearchConfigSheet campaignId={campaignId} />

      {/* Chat panel */}
      <ChatPanel
        open={chatOpen}
        onClose={() => setChatOpen(false)}
        contextId={campaignId}
      />

      {/* Activity feed */}
      <ActivityFeed campaignId={campaignId} />
    </div>
  );
}

"use client";

import { useState, useEffect, useCallback } from "react";
import { Heart, LayoutGrid, Settings } from "lucide-react";
import { useCampaignStore } from "@/stores/campaign-store";
import { useListingStore } from "@/stores/listing-store";
import { useResearchStore } from "@/stores/research-store";
import { useActivityStore } from "@/stores/activity-store";
import { useScanStreamStore } from "@/stores/scan-stream-store";
import { useCampaign } from "@/hooks/use-campaign";
import { useScanStream } from "@/hooks/use-scan-stream";
import { useResearchStream } from "@/hooks/use-research-stream";
import { DiscoverScreen } from "@/components/discover/discover-screen";
import { TrackScreen } from "@/components/track/track-screen";
import { SettingsScreen } from "@/components/settings/settings-screen";
import { CampaignPill } from "@/components/shared/campaign-pill";
import { CampaignDropdown } from "@/components/shared/campaign-dropdown";
import { CampaignActions } from "@/components/shared/campaign-actions";
import type { Campaign } from "@/types";

type Tab = "discover" | "track" | "settings";

const TABS: { key: Tab; icon: typeof Heart; label: string }[] = [
  { key: "discover", icon: Heart, label: "Discover" },
  { key: "track", icon: LayoutGrid, label: "Track" },
  { key: "settings", icon: Settings, label: "Settings" },
];

interface AppProps {
  campaignId: string;
  campaigns: Campaign[];
  onSwitch: (campaignId: string) => void;
  onCreate: () => void;
}

export function App({ campaignId, campaigns, onSwitch, onCreate }: AppProps) {
  const [activeTab, setActiveTab] = useState<Tab>("discover");
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [actionsCampaign, setActionsCampaign] = useState<Campaign | null>(null);

  // Use selectors to avoid subscribing to entire stores
  const campaign = useCampaignStore((s) => s.campaign);
  const fetchStats = useCampaignStore((s) => s.fetchStats);
  const statsMap = useCampaignStore((s) => s.statsMap);
  const archiveCampaign = useCampaignStore((s) => s.archiveCampaign);
  const fetchListings = useListingStore((s) => s.fetchListings);
  const isScanning = useActivityStore((s) => s.isScanning);
  const latestScan = useActivityStore((s) => s.latestScan);
  const fetchScans = useActivityStore((s) => s.fetchScans);
  const fetchActivities = useActivityStore((s) => s.fetchActivities);
  const scanStatus = useScanStreamStore((s) => s.status);
  const fetchAllResearch = useResearchStore((s) => s.fetchAllResearch);
  const researching = useResearchStore((s) => s.researching);

  const hasActiveResearch = Object.values(researching).some(
    (r) => r.status === "queued" || r.status === "running"
  );

  // Load campaign data + poll
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
  }, [scanStatus, campaignId, fetchListings, fetchStats, fetchScans, fetchActivities]);

  // Load research data on mount
  useEffect(() => {
    fetchAllResearch(campaignId);
  }, [campaignId, fetchAllResearch]);

  const handleArchive = useCallback(
    async (id: string) => {
      await archiveCampaign(id);
      // If we archived the current campaign, switch will be handled by page.tsx
    },
    [archiveCampaign]
  );

  const handleSelect = useCallback(
    (id: string) => {
      setDropdownOpen(false);
      if (id !== campaignId) {
        onSwitch(id);
      }
    },
    [campaignId, onSwitch]
  );

  // Build scanning campaign IDs set
  const scanningCampaignIds = new Set<string>();
  if (isScanning) {
    scanningCampaignIds.add(campaignId);
  }

  if (!campaign) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: "var(--cream)" }}>
        <div className="animate-pulse" style={{ color: "var(--ink-50)" }}>
          Loading...
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen overflow-hidden" style={{ background: "var(--cream)" }}>
      {/* Active screen */}
      <div className="flex-1 overflow-hidden relative">
        {activeTab === "discover" && (
          <DiscoverScreen
            campaignId={campaignId}
            campaignPill={
              <CampaignPill
                campaign={campaign}
                onClick={() => setDropdownOpen(true)}
              />
            }
          />
        )}
        {activeTab === "track" && (
          <TrackScreen
            campaignId={campaignId}
            campaignPill={
              <CampaignPill
                campaign={campaign}
                onClick={() => setDropdownOpen(true)}
              />
            }
          />
        )}
        {activeTab === "settings" && (
          <SettingsScreen
            campaignId={campaignId}
            campaignPill={
              <CampaignPill
                campaign={campaign}
                onClick={() => setDropdownOpen(true)}
              />
            }
          />
        )}
      </div>

      {/* Bottom nav */}
      <nav
        className="flex-shrink-0 flex items-center justify-around"
        style={{
          height: 80,
          borderTop: "1px solid var(--ink-08)",
          background: "var(--cream)",
          paddingBottom: "env(safe-area-inset-bottom, 0px)",
        }}
      >
        {TABS.map(({ key, icon: Icon, label }) => {
          const isActive = activeTab === key;
          return (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              className="flex flex-col items-center gap-1 py-2 px-4"
              style={{ color: isActive ? "var(--terra)" : "var(--ink-30)" }}
            >
              <Icon size={22} fill={key === "discover" && isActive ? "var(--terra)" : "none"} />
              <span className="text-[11px] font-medium">{label}</span>
            </button>
          );
        })}
      </nav>

      {/* Campaign dropdown */}
      <CampaignDropdown
        open={dropdownOpen}
        onClose={() => setDropdownOpen(false)}
        campaigns={campaigns}
        activeCampaignId={campaignId}
        stats={statsMap}
        scanningCampaignIds={scanningCampaignIds}
        onSelect={handleSelect}
        onCreate={onCreate}
        onOpenActions={(c) => {
          setDropdownOpen(false);
          setActionsCampaign(c);
        }}
      />

      {/* Campaign actions sheet */}
      <CampaignActions
        open={!!actionsCampaign}
        onClose={() => setActionsCampaign(null)}
        campaign={actionsCampaign}
        onArchive={handleArchive}
      />
    </div>
  );
}

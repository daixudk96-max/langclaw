"use client";

import { useEffect, useState, useCallback } from "react";
import { SetupWizard } from "@/components/setup/setup-wizard";
import { App } from "@/components/app/app";
import { useCampaignStore } from "@/stores/campaign-store";

const STORAGE_KEY = "rentagent_active_campaign_id";

export default function Home() {
  // Use selectors to avoid subscribing to entire store
  const campaigns = useCampaignStore((s) => s.campaigns);
  const fetchCampaigns = useCampaignStore((s) => s.fetchCampaigns);
  const fetchAllStats = useCampaignStore((s) => s.fetchAllStats);

  const [activeCampaignId, setActiveCampaignId] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [isCreating, setIsCreating] = useState(false);

  // Filter to only active campaigns
  const activeCampaigns = campaigns.filter((c) => c.status === "active");

  // Load campaigns and restore persisted selection
  useEffect(() => {
    fetchCampaigns().then(() => setReady(true));
  }, [fetchCampaigns]);

  // Once ready, restore from localStorage or pick first active
  useEffect(() => {
    if (!ready) return;
    if (activeCampaignId) return;

    const stored = localStorage.getItem(STORAGE_KEY);
    const storedCampaign = stored
      ? activeCampaigns.find((c) => c.id === stored)
      : null;

    const selected =
      storedCampaign ?? activeCampaigns[0] ?? null;

    if (selected) {
      setActiveCampaignId(selected.id);
    }
  }, [ready, activeCampaigns, activeCampaignId]);

  // Persist selection to localStorage
  useEffect(() => {
    if (activeCampaignId) {
      localStorage.setItem(STORAGE_KEY, activeCampaignId);
    }
  }, [activeCampaignId]);

  // Fetch stats for all active campaigns (for the dropdown)
  useEffect(() => {
    if (ready && activeCampaigns.length > 0) {
      fetchAllStats(activeCampaigns.map((c) => c.id));
    }
  }, [ready, activeCampaigns, fetchAllStats]);

  const handleSwitch = useCallback((campaignId: string) => {
    setActiveCampaignId(campaignId);
  }, []);

  const handleCreateNew = useCallback(() => {
    setIsCreating(true);
  }, []);

  const handleWizardComplete = useCallback((id: string) => {
    setActiveCampaignId(id);
    setIsCreating(false);
  }, []);

  if (!ready) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: "var(--cream)" }}>
        <div className="text-center space-y-2">
          <div
            className="w-8 h-8 border-2 border-t-transparent rounded-full animate-spin mx-auto"
            style={{ borderColor: "var(--terra)", borderTopColor: "transparent" }}
          />
          <p className="text-sm" style={{ color: "var(--ink-50)" }}>Loading...</p>
        </div>
      </div>
    );
  }

  // Show wizard if creating new campaign or no active campaigns
  if (isCreating || activeCampaigns.length === 0) {
    return (
      <SetupWizard
        onComplete={handleWizardComplete}
      />
    );
  }

  // Edge case: stored campaign was archived
  if (!activeCampaignId || !activeCampaigns.find((c) => c.id === activeCampaignId)) {
    const firstActive = activeCampaigns[0];
    if (firstActive) {
      setActiveCampaignId(firstActive.id);
    }
    return null;
  }

  return (
    <App
      campaignId={activeCampaignId}
      campaigns={activeCampaigns}
      onSwitch={handleSwitch}
      onCreate={handleCreateNew}
    />
  );
}

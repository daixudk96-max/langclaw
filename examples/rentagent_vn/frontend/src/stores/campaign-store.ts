import { create } from "zustand";
import type { Campaign, CampaignStats } from "@/types";
import * as api from "@/lib/api";

interface CampaignState {
  campaign: Campaign | null;
  campaigns: Campaign[];
  stats: CampaignStats | null;
  statsMap: Record<string, CampaignStats | null>;
  loading: boolean;
  error: string | null;

  // Actions
  fetchCampaigns: () => Promise<void>;
  fetchCampaign: (id: string) => Promise<void>;
  fetchStats: (id: string) => Promise<void>;
  fetchAllStats: (ids: string[]) => Promise<void>;
  createCampaign: (data: Parameters<typeof api.createCampaign>[0]) => Promise<Campaign>;
  updateCampaign: (id: string, data: Parameters<typeof api.updateCampaign>[1]) => Promise<void>;
  archiveCampaign: (id: string) => Promise<void>;
  setCampaign: (campaign: Campaign | null) => void;
  setOutreachAutoSend: (campaignId: string, autoSend: boolean) => Promise<void>;
  clearError: () => void;
}

export const useCampaignStore = create<CampaignState>((set, get) => ({
  campaign: null,
  campaigns: [],
  stats: null,
  statsMap: {},
  loading: false,
  error: null,

  fetchCampaigns: async () => {
    set({ loading: true, error: null });
    try {
      const campaigns = await api.listCampaigns();
      set({ campaigns, loading: false });
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
    }
  },

  fetchCampaign: async (id) => {
    // Only show loading state on the very first fetch (no campaign yet).
    // Subsequent refetches update silently to avoid triggering parent
    // re-renders that would unmount/remount the Dashboard.
    if (!get().campaign) {
      set({ loading: true, error: null });
    }
    try {
      const campaign = await api.getCampaign(id);
      set({ campaign, loading: false });
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
    }
  },

  fetchStats: async (id) => {
    try {
      const stats = await api.getCampaignStats(id);
      set((s) => ({
        stats,
        statsMap: { ...s.statsMap, [id]: stats },
      }));
    } catch (e) {
      console.error("Failed to fetch stats:", e);
    }
  },

  fetchAllStats: async (ids) => {
    const results = await Promise.allSettled(
      ids.map((id) => api.getCampaignStats(id))
    );
    const newStatsMap: Record<string, CampaignStats | null> = {};
    results.forEach((result, index) => {
      const id = ids[index];
      if (result.status === "fulfilled") {
        newStatsMap[id] = result.value;
      } else {
        newStatsMap[id] = null;
      }
    });
    set((s) => ({
      statsMap: { ...s.statsMap, ...newStatsMap },
    }));
  },

  createCampaign: async (data) => {
    set({ loading: true, error: null });
    try {
      const campaign = await api.createCampaign(data);
      set((s) => ({
        campaign,
        campaigns: [campaign, ...s.campaigns],
        loading: false,
      }));
      return campaign;
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
      throw e;
    }
  },

  updateCampaign: async (id, data) => {
    try {
      const campaign = await api.updateCampaign(id, data);
      set((s) => ({
        campaign: s.campaign?.id === id ? campaign : s.campaign,
        campaigns: s.campaigns.map((c) => (c.id === id ? campaign : c)),
      }));
    } catch (e) {
      set({ error: (e as Error).message });
    }
  },

  archiveCampaign: async (id) => {
    try {
      await api.updateCampaign(id, { status: "archived" });
      set((s) => ({
        campaigns: s.campaigns.filter((c) => c.id !== id),
        campaign: s.campaign?.id === id ? null : s.campaign,
      }));
    } catch (e) {
      set({ error: (e as Error).message });
      throw e;
    }
  },

  setCampaign: (campaign) => set({ campaign }),

  setOutreachAutoSend: async (campaignId, autoSend) => {
    const current = get().campaign;
    if (!current || current.id !== campaignId) return;

    const updatedPreferences = {
      ...current.preferences,
      outreach_auto_send: autoSend,
    };

    try {
      const campaign = await api.updateCampaign(campaignId, {
        preferences: updatedPreferences,
      });
      set((s) => ({
        campaign: s.campaign?.id === campaignId ? campaign : s.campaign,
        campaigns: s.campaigns.map((c) => (c.id === campaignId ? campaign : c)),
      }));
    } catch (e) {
      set({ error: (e as Error).message });
      throw e;
    }
  },

  clearError: () => set({ error: null }),
}));

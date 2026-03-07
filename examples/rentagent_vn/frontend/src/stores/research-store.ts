import { create } from "zustand";
import type {
  AreaResearch,
  AutoOutreachConfig,
  ResearchCriteriaOption,
  ResearchSSEEvent,
} from "@/types";
import { DEFAULT_CRITERIA } from "@/types";
import * as api from "@/lib/api";

interface ResearchState {
  // Card selection (for batch research)
  selectedIds: Set<string>;
  toggleSelection: (id: string) => void;
  selectAll: (ids: string[]) => void;
  clearSelection: () => void;

  // Research config
  criteria: ResearchCriteriaOption[];
  autoOutreach: AutoOutreachConfig;
  setCriteria: (criteria: ResearchCriteriaOption[]) => void;
  setAutoOutreach: (config: AutoOutreachConfig) => void;

  // Active research tracking
  researching: Record<string, AreaResearch>; // research_id -> data
  researchByListing: Record<string, string>; // listing_id -> research_id
  startResearch: (campaignId: string, listingIds: string[]) => Promise<void>;
  fetchAllResearch: (campaignId: string) => Promise<void>;
  fetchResearch: (campaignId: string, researchId: string) => Promise<void>;
  retryResearch: (campaignId: string, researchId: string) => Promise<void>;

  // SSE updates
  updateFromSSE: (event: ResearchSSEEvent) => void;

  // Config sheet visibility
  configSheetOpen: boolean;
  setConfigSheetOpen: (open: boolean) => void;

  // Loading
  loading: boolean;
  error: string | null;
}

export const useResearchStore = create<ResearchState>((set, get) => ({
  selectedIds: new Set<string>(),
  criteria: DEFAULT_CRITERIA.map((c) => ({ ...c })),
  autoOutreach: {
    enabled: false,
    threshold: 7.0,
    must_pass: {},
    message_template: "",
  },
  researching: {},
  researchByListing: {},
  configSheetOpen: false,
  loading: false,
  error: null,

  toggleSelection: (id) =>
    set((s) => {
      const next = new Set(s.selectedIds);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return { selectedIds: next };
    }),

  selectAll: (ids) => set({ selectedIds: new Set(ids) }),

  clearSelection: () => set({ selectedIds: new Set() }),

  setCriteria: (criteria) => set({ criteria }),

  setAutoOutreach: (config) => set({ autoOutreach: config }),

  setConfigSheetOpen: (open) => set({ configSheetOpen: open }),

  startResearch: async (campaignId, listingIds) => {
    const { criteria, autoOutreach } = get();
    const enabledCriteria = criteria.filter((c) => c.enabled).map((c) => c.key);

    try {
      set({ loading: true, error: null });
      await api.triggerResearch(campaignId, {
        listing_ids: listingIds,
        criteria: enabledCriteria,
        auto_outreach: autoOutreach.enabled
          ? {
              enabled: true,
              threshold: autoOutreach.threshold,
              must_pass: autoOutreach.must_pass,
              message_template: autoOutreach.message_template || undefined,
            }
          : { enabled: false, threshold: 7.0, must_pass: {} },
      });
      set({ selectedIds: new Set(), configSheetOpen: false, loading: false });
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
    }
  },

  fetchAllResearch: async (campaignId) => {
    try {
      const items = await api.listResearch(campaignId);
      const researching: Record<string, AreaResearch> = {};
      const researchByListing: Record<string, string> = {};
      for (const item of items) {
        researching[item.id] = item;
        researchByListing[item.listing_id] = item.id;
      }
      set({ researching, researchByListing });
    } catch {
      // Silently ignore — research data is optional
    }
  },

  fetchResearch: async (campaignId, researchId) => {
    try {
      const item = await api.getResearch(campaignId, researchId);
      set((s) => ({
        researching: { ...s.researching, [item.id]: item },
        researchByListing: {
          ...s.researchByListing,
          [item.listing_id]: item.id,
        },
      }));
    } catch {
      // Ignore
    }
  },

  retryResearch: async (campaignId, researchId) => {
    try {
      const item = await api.retryResearch(campaignId, researchId);
      set((s) => ({
        researching: { ...s.researching, [item.id]: item },
      }));
    } catch (e) {
      set({ error: (e as Error).message });
    }
  },

  updateFromSSE: (event) => {
    if (!event.research_id) return;
    set((s) => {
      const existing = s.researching[event.research_id!];
      if (!existing) return s;

      const updated = { ...existing };
      if (event.type === "started") {
        updated.status = "running";
      } else if (event.type === "completed") {
        updated.status = "done";
        updated.overall_score = event.overall_score ?? null;
        updated.verdict = event.verdict ?? null;
      } else if (event.type === "failed") {
        updated.status = "failed";
        updated.error_message = event.error ?? null;
      }

      return {
        researching: { ...s.researching, [event.research_id!]: updated },
      };
    });
  },
}));

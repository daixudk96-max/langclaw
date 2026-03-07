"use client";

import { useEffect, useRef } from "react";
import { useResearchStore } from "@/stores/research-store";
import { useListingStore } from "@/stores/listing-store";
import type { ResearchSSEEvent } from "@/types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Hook that connects to the research SSE stream when research is active.
 * Updates the research store with progress events and refetches listings
 * when research completes.
 */
export function useResearchStream(campaignId: string, active: boolean) {
  const { updateFromSSE, fetchAllResearch } = useResearchStore();
  const { fetchListings } = useListingStore();
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!active || !campaignId) {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      return;
    }

    const url = `${BASE_URL}/api/v1/campaigns/${campaignId}/research/stream`;
    const eventSource = new EventSource(url);
    eventSourceRef.current = eventSource;

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as ResearchSSEEvent;
        updateFromSSE(data);

        // On completion or failure, refetch to get full data
        if (data.type === "completed" || data.type === "failed") {
          fetchAllResearch(campaignId);
          fetchListings(campaignId);
        }

        // Close connection when all research jobs are done
        if (data.type === "done") {
          eventSource.close();
          eventSourceRef.current = null;
          fetchAllResearch(campaignId);
          fetchListings(campaignId);
        }
      } catch {
        console.error("Failed to parse research SSE event:", event.data);
      }
    };

    eventSource.onerror = () => {
      console.warn("Research SSE connection error or closed");
    };

    return () => {
      eventSource.close();
      eventSourceRef.current = null;
    };
  }, [active, campaignId, updateFromSSE, fetchAllResearch, fetchListings]);
}

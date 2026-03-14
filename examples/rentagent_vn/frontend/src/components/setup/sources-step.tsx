"use client";

import { useState, useMemo } from "react";
import { ArrowLeft, Plus, Globe } from "lucide-react";
import type { CampaignPreferences } from "@/types";
import {
  SourceCard,
  CustomSourceCard,
  DEFAULT_SOURCES,
  DISTRICT_GROUPS,
  getPlatformFromUrl,
  type Source,
} from "@/components/shared";

interface SourcesStepProps {
  preferences: CampaignPreferences;
  onConfirm: (sources: string[]) => void;
  onBack: () => void;
}

export function SourcesStep({ preferences, onConfirm, onBack }: SourcesStepProps) {
  const [defaults, setDefaults] = useState<Source[]>(() =>
    DEFAULT_SOURCES.map((s) => ({ ...s, enabled: true }))
  );
  const [customSources, setCustomSources] = useState<Source[]>([]);
  const [urlInput, setUrlInput] = useState("");
  const [error, setError] = useState("");

  const districtSuggestions = useMemo(() => {
    if (!preferences.district) return [];

    const suggestions: Source[] = [];
    const districts = preferences.district.split(/[,，、]/);

    for (const district of districts) {
      const trimmed = district.trim();
      const groups = DISTRICT_GROUPS[trimmed];
      if (groups) {
        for (const group of groups) {
          if (!suggestions.find((s) => s.url === group.url)) {
            suggestions.push({
              ...group,
              platform: "facebook",
              enabled: true,
            });
          }
        }
      }
    }

    return suggestions;
  }, [preferences.district]);

  const [districtSources, setDistrictSources] =
    useState<Source[]>(districtSuggestions);

  const toggleDefault = (index: number) => {
    setDefaults((prev) =>
      prev.map((s, i) => (i === index ? { ...s, enabled: !s.enabled } : s))
    );
  };

  const toggleDistrict = (index: number) => {
    setDistrictSources((prev) =>
      prev.map((s, i) => (i === index ? { ...s, enabled: !s.enabled } : s))
    );
  };

  const addCustomUrl = () => {
    const url = urlInput.trim();
    if (!url) return;

    if (!url.startsWith("http")) {
      setError("Invalid URL");
      return;
    }

    const allUrls = [
      ...defaults.map((s) => s.url),
      ...districtSources.map((s) => s.url),
      ...customSources.map((s) => s.url),
    ];

    if (allUrls.includes(url)) {
      setError("This URL is already added");
      return;
    }

    try {
      const platform = getPlatformFromUrl(url);
      const label = new URL(url).hostname.replace("www.", "");

      setCustomSources((prev) => [
        ...prev,
        { url, label, platform, enabled: true },
      ]);
      setUrlInput("");
      setError("");
    } catch {
      setError("Invalid URL");
    }
  };

  const removeCustom = (url: string) => {
    setCustomSources((prev) => prev.filter((s) => s.url !== url));
  };

  const handleConfirm = () => {
    const sources = [
      ...defaults.filter((s) => s.enabled).map((s) => s.url),
      ...districtSources.filter((s) => s.enabled).map((s) => s.url),
      ...customSources.filter((s) => s.enabled).map((s) => s.url),
    ];
    onConfirm(sources);
  };

  const totalSources =
    defaults.filter((s) => s.enabled).length +
    districtSources.filter((s) => s.enabled).length +
    customSources.filter((s) => s.enabled).length;

  return (
    <div
      className="flex flex-col min-h-screen"
      style={{ background: "var(--cream)" }}
    >
      {/* Header */}
      <div className="flex-shrink-0 pt-[60px] px-5 pb-6">
        <button
          onClick={onBack}
          className="flex items-center gap-1 text-[13px] font-medium mb-4 -ml-1"
          style={{ color: "var(--ink-50)" }}
        >
          <ArrowLeft size={16} />
          Back
        </button>
        <h1
          className="text-[22px] font-extrabold tracking-tight"
          style={{ color: "var(--ink)" }}
        >
          Choose your sources
        </h1>
        <p
          className="text-[13px] font-medium mt-1"
          style={{ color: "var(--ink-50)" }}
        >
          We&apos;ll scan these sites to find listings for you
        </p>
      </div>

      {/* Content */}
      <div className="flex-1 px-5 overflow-y-auto pb-4">
        {/* Default sources */}
        <div className="mb-6">
          <p
            className="text-[11px] font-semibold uppercase tracking-wide mb-3"
            style={{ color: "var(--ink-30)", letterSpacing: "0.8px" }}
          >
            Popular Sources
          </p>
          <div className="flex flex-col gap-2">
            {defaults.map((source, i) => (
              <SourceCard
                key={source.url}
                source={source}
                onToggle={() => toggleDefault(i)}
              />
            ))}
          </div>
        </div>

        {/* District suggestions */}
        {districtSources.length > 0 && (
          <div className="mb-6">
            <p
              className="text-[11px] font-semibold uppercase tracking-wide mb-1"
              style={{ color: "var(--ink-30)", letterSpacing: "0.8px" }}
            >
              District Suggestions
            </p>
            <p
              className="text-[12px] mb-3"
              style={{ color: "var(--ink-30)" }}
            >
              Based on your area: {preferences.district}
            </p>
            <div className="flex flex-col gap-2">
              {districtSources.map((source, i) => (
                <SourceCard
                  key={source.url}
                  source={source}
                  onToggle={() => toggleDistrict(i)}
                />
              ))}
            </div>
          </div>
        )}

        {/* Custom sources */}
        <div>
          <p
            className="text-[11px] font-semibold uppercase tracking-wide mb-3"
            style={{ color: "var(--ink-30)", letterSpacing: "0.8px" }}
          >
            Add Custom Source
          </p>

          {customSources.length > 0 && (
            <div className="flex flex-col gap-2 mb-3">
              {customSources.map((source) => (
                <CustomSourceCard
                  key={source.url}
                  source={source}
                  onRemove={() => removeCustom(source.url)}
                />
              ))}
            </div>
          )}

          <div
            className="flex items-center gap-2 p-3"
            style={{
              background: "var(--ds-white)",
              border: "1px solid var(--ink-15)",
              borderRadius: "var(--r-lg)",
            }}
          >
            <Globe size={18} style={{ color: "var(--ink-30)" }} />
            <input
              value={urlInput}
              onChange={(e) => {
                setUrlInput(e.target.value);
                setError("");
              }}
              onKeyDown={(e) =>
                e.key === "Enter" && (e.preventDefault(), addCustomUrl())
              }
              placeholder="Paste Facebook group or Zalo link..."
              className="flex-1 bg-transparent outline-none text-[13px] font-medium"
              style={{ color: "var(--ink)" }}
            />
            <button
              onClick={addCustomUrl}
              disabled={!urlInput.trim()}
              className="w-10 h-10 rounded-full flex items-center justify-center transition-colors"
              style={{
                background: urlInput.trim() ? "var(--terra)" : "var(--ink-08)",
              }}
            >
              <Plus
                size={20}
                style={{ color: urlInput.trim() ? "white" : "var(--ink-30)" }}
              />
            </button>
          </div>
          {error && (
            <p className="text-[12px] mt-2" style={{ color: "#C03" }}>
              {error}
            </p>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="flex-shrink-0 px-5 pt-4 pb-8">
        <button
          onClick={handleConfirm}
          disabled={totalSources === 0}
          className="w-full h-[52px] text-[15px] font-semibold transition-colors"
          style={{
            background: totalSources > 0 ? "var(--terra)" : "var(--ink-15)",
            color: totalSources > 0 ? "white" : "var(--ink-30)",
            borderRadius: "var(--r-lg)",
          }}
        >
          {totalSources === 0
            ? "Select at least one source"
            : `Continue with ${totalSources} source${totalSources > 1 ? "s" : ""}`}
        </button>
      </div>
    </div>
  );
}

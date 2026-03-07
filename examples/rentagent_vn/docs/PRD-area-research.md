# PRD: Area Research & Auto-Outreach

**Author:** PM
**Status:** Draft
**Date:** 2026-03-07
**Target:** RentAgent VN (`examples/rentagent_vn/`)

---

## 1. Problem

Users currently see new listings in the "Moi" column and must manually research each neighborhood before deciding to contact the landlord. This involves:
- Opening Google Maps, searching the address, checking nearby amenities
- Using Street View to assess the alley/street condition
- Repeating this for every listing (10-50+ per scan)

This is the most time-consuming step in the rental pipeline. Users skip it (making uninformed decisions) or burn out doing it manually.

## 2. Solution

Add an **Area Research** step between "Moi" (new) and "Da lien he" (contacted). The TinyFish agent autonomously visits Google Maps for each selected listing's address, searches for nearby amenities, walks Street View, and returns a structured neighborhood assessment with scores. Optionally, if scores meet user-defined thresholds, the system auto-drafts and sends outreach messages to the landlord.

---

## 3. Pipeline Change

### Current
```
Moi -> Da lien he -> Hen xem -> Da xem -> Chon -> Bo qua
```

### Proposed
```
Moi -> Dang khao sat -> Da lien he -> Hen xem -> Da xem -> Chon -> Bo qua
```

New stage: `"researching"` with label **"Dang khao sat"** (teal-500).

Substates within `researching`:
| Substate | Meaning |
|----------|---------|
| `queued` | Waiting to be processed |
| `running` | TinyFish agent is actively researching |
| `done` | Research complete, results available |
| `failed` | Agent failed (timeout, Maps error, etc.) |

---

## 4. UX Design

### 4.1 Initiating Research — Batch Action Bar

**Trigger:** User selects one or more listing cards in the "Moi" column via checkboxes.

When >= 1 card is selected, a **floating action bar** appears at the bottom of the pipeline view:

```
+-----------------------------------------------------------------------+
|  [x] 3 selected    [ Khao sat khu vuc ]  [ Bo qua ]  [ Huy chon ]   |
+-----------------------------------------------------------------------+
```

- **"Khao sat khu vuc"** (Research area) button opens the **Research Config Sheet**.
- **"Bo qua"** triggers the existing skip dialog.
- **"Huy chon"** clears selection.

The floating bar uses `position: sticky; bottom: 0` so it's always visible even when scrolling through listings.

### 4.2 Research Config Sheet (Bottom Sheet / Dialog)

When the user clicks "Khao sat khu vuc", a sheet slides up with:

```
+---------------------------------------------------------------+
|  Khao sat khu vuc (3 listings)                            [X] |
+---------------------------------------------------------------+
|                                                               |
|  TIEU CHI DANH GIA (Research Criteria)                        |
|  Select which aspects to evaluate:                            |
|                                                               |
|  [v] An uong & Mua sam        (Food & Shopping)              |
|  [v] Y te                     (Healthcare)                    |
|  [v] Giao duc & Gia dinh      (Education & Family)            |
|  [v] Giao thong               (Transportation)                |
|  [ ] Giai tri & The thao      (Entertainment & Sports)        |
|  [v] Duong pho & Ve sinh      (Street Atmosphere)             |
|  [v] An ninh                  (Security)                      |
|                                                               |
|  ─────────────────────────────────────────────────────────     |
|                                                               |
|  TU DONG LIEN HE (Auto-outreach)            [  toggle OFF  ] |
|                                                               |
|  (collapsed when OFF, expands when ON:)                       |
|                                                               |
|  Gui tin nhan tu dong neu diem trung binh >= [ 7.0 /10 ]      |
|                                                               |
|  Dieu kien bat buoc (must-pass):                              |
|  [ ] An ninh >= 6                                             |
|  [ ] Giao thong >= 5                                          |
|  [ ] Duong pho >= 6                                           |
|                                                               |
|  Mau tin nhan:                                                |
|  +-----------------------------------------------------------+|
|  | Xin chao anh/chi {landlord_name},                         ||
|  | Toi thay bai dang cho thue tai {address} va rat quan tam. ||
|  | Xin hoi phong con trong khong a?                          ||
|  +-----------------------------------------------------------+|
|  |  [ Tao mau moi voi AI ]                                  ||
|  +-----------------------------------------------------------+|
|                                                               |
|          [ Bat dau khao sat ]                                 |
+---------------------------------------------------------------+
```

**Key decisions:**
- **Criteria selection** defaults to all checked. Users can uncheck criteria they don't care about. Unchecked criteria are not researched (saves agent time/cost).
- **Auto-outreach toggle** is OFF by default. When ON, reveals threshold config.
- **Overall threshold** is a single average score slider (1-10, default 7.0).
- **Must-pass conditions** are optional per-criteria minimum scores. If any must-pass fails, outreach is blocked regardless of average.
- **Message template** uses `{variable}` interpolation. User can edit freely or click "Tao mau moi voi AI" to have the LLM generate a new template based on the listing context.

### 4.3 Research Progress — In-Column Status

After starting, selected listings move to the "Dang khao sat" column. Each card shows a status indicator:

```
+------------------------------------------+
| Dang khao sat (3)                        |
+------------------------------------------+
|                                          |
|  +--------------------------------------+|
|  | [img] 2PN Nguyen Huu Canh            ||
|  |       8 trieu/th - Binh Thanh        ||
|  |       [=====>........] Dang khao sat  ||
|  +--------------------------------------+|
|                                          |
|  +--------------------------------------+|
|  | [img] Studio Vo Van Kiet             ||
|  |       5.5 trieu/th - Quan 1          ||
|  |       [==============] Done  8.2/10  ||
|  +--------------------------------------+|
|                                          |
|  +--------------------------------------+|
|  | [img] 3PN Le Van Sy                  ||
|  |       12 trieu/th - Quan 3           ||
|  |       [ queued... ]                  ||
|  +--------------------------------------+|
```

- **Queued:** Gray pulsing dot + "Cho xu ly"
- **Running:** Animated progress bar + "Dang khao sat"
- **Done:** Green check + overall score badge (e.g., "8.2/10")
- **Failed:** Red exclamation + "Loi" with retry icon

Clicking a completed card opens the **Research Results Panel**.

### 4.4 Research Results Panel

Replaces or extends the existing `listing-detail.tsx` right panel. When a researched listing is selected:

**Tab 1: Tong quan (Overview)** — the default view

```
+---------------------------------------------------------------+
|  280/126/3 Bui Huu Nghia, P.2, Binh Thanh                    |
|                                                               |
|  DIEM TONG       8.2 / 10       "Rat tot"                    |
|  ============================================                 |
|                                                               |
|  +-------------------+  +-------------------+                 |
|  | An uong & Mua sam |  | Y te              |                 |
|  |    [=======] 9/10  |  |    [======] 7/10  |                 |
|  +-------------------+  +-------------------+                 |
|  +-------------------+  +-------------------+                 |
|  | Giao duc          |  | Giao thong        |                 |
|  |    [========] 8/10 |  |    [=====] 7/10   |                 |
|  +-------------------+  +-------------------+                 |
|  +-------------------+  +-------------------+                 |
|  | Duong pho & VS    |  | An ninh           |                 |
|  |    [=========] 9/10|  |    [========] 8/10|                 |
|  +-------------------+  +-------------------+                 |
|                                                               |
|  NHAN DINH CHUNG                                              |
|  "Lua chon tot cho gia dinh, hem yeu tinh va sach se,         |
|   gan truong quoc te va cho truyen thong."                    |
|                                                               |
|  [ Lien he ngay ]   [ Bo qua ]   [ Khao sat lai ]            |
+---------------------------------------------------------------+
```

The overall score uses a color scale:
- 1-3: Red (Kem)
- 4-5: Orange (Trung binh)
- 6-7: Yellow-green (Kha)
- 8-9: Green (Tot / Rat tot)
- 10: Emerald (Tuyet voi)

**Tab 2: Chi tiet (Details)** — expandable sections per criterion

```
+---------------------------------------------------------------+
|  AN UONG & MUA SAM                              9/10    [v]   |
|  ----------------------------------------------------------   |
|  Quan an:   Mat do cao — Quan An Gia Dinh Hoa Teo,            |
|             Thanh Canh Bun, nhieu quan com binh dan            |
|  Thuc pham: TrueOrganic, FarmShop (rau sach)                  |
|  Tien loi:  Circle K cach 200m, tap hoa nhieu                 |
|  Khoang cach: Di bo duoc (< 500m)                             |
|                                                               |
|  Y TE                                            7/10    [>]  |
|  GIAO DUC & GIA DINH                             8/10    [>]  |
|  GIAO THONG                                       7/10    [>]  |
|  DUONG PHO & VE SINH                              9/10    [>]  |
|  AN NINH                                          8/10    [>]  |
+---------------------------------------------------------------+
```

Each section expands accordion-style to show the detailed findings.

**Tab 3: Street View** — embedded Street View snapshots or link

If TinyFish captured Street View screenshots during research, display them here as a mini gallery. Otherwise, provide a "Xem tren Google Maps" link that opens the address in Maps.

### 4.5 Auto-Outreach Feedback

When auto-outreach is enabled and a listing passes the threshold:

1. A toast notification appears: "Da tu dong gui tin nhan cho {landlord_name} (diem: 8.2/10)"
2. The listing automatically moves to "Da lien he" stage.
3. The outreach message is logged in `outreach_messages` with status `sent`.
4. Activity log records: `event_type: "auto_outreach_sent"`.

When a listing fails the threshold:
1. The listing stays in "Dang khao sat" with `done` status.
2. A subtle label on the card shows: "Khong dat nguong (6.1/10)" in orange text.
3. User can still manually click "Lien he ngay" to override.

---

## 5. Data Model

### 5.1 New Table: `area_research`

```sql
CREATE TABLE IF NOT EXISTS area_research (
  id TEXT PRIMARY KEY DEFAULT (hex(randomblob(6))),
  listing_id TEXT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
  campaign_id TEXT NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
  status TEXT NOT NULL DEFAULT 'queued',       -- queued | running | done | failed
  criteria_json TEXT NOT NULL DEFAULT '[]',     -- which criteria were requested
  scores_json TEXT,                             -- per-criteria scores + overall
  result_json TEXT,                             -- full structured assessment
  verdict TEXT,                                 -- one-line summary
  overall_score REAL,                           -- 0.0 - 10.0
  street_view_urls_json TEXT DEFAULT '[]',      -- captured Street View screenshots
  auto_outreach_enabled INTEGER DEFAULT 0,
  auto_outreach_threshold REAL,                 -- minimum average to trigger
  auto_outreach_conditions_json TEXT,            -- must-pass per-criteria minimums
  auto_outreach_triggered INTEGER DEFAULT 0,    -- 1 if outreach was auto-sent
  tinyfish_job_id TEXT,                         -- TinyFish job reference
  error_message TEXT,
  started_at TEXT,
  completed_at TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_area_research_listing ON area_research(listing_id);
CREATE INDEX IF NOT EXISTS idx_area_research_campaign ON area_research(campaign_id);
CREATE INDEX IF NOT EXISTS idx_area_research_status ON area_research(campaign_id, status);
```

### 5.2 `scores_json` Structure

```json
{
  "overall": 8.2,
  "criteria": {
    "food_shopping": {
      "score": 9,
      "label": "An uong & Mua sam",
      "highlights": [
        "Mat do quan an cao, da dang",
        "Co cua hang thuc pham sach (TrueOrganic, FarmShop)",
        "Circle K cach 200m"
      ],
      "details": {
        "dining": "high density of local restaurants",
        "specialty": "TrueOrganic, FarmShop for fresh produce",
        "convenience": "Circle K, local mom-and-pop shops"
      },
      "walking_distance": true
    },
    "healthcare": {
      "score": 7,
      "label": "Y te",
      "highlights": [
        "Nhieu phong kham tu nhan",
        "Tram y te phuong 24/24"
      ],
      "details": {
        "clinics": "several private clinics, dental, dermatology",
        "public_services": "Ward Medical Center (24h)"
      }
    },
    "education_family": {
      "score": 8,
      "label": "Giao duc & Gia dinh",
      "highlights": [
        "Truong mam non quoc te (Kindy City, HEI Schools)",
        "Truong tieu hoc Lam Son"
      ],
      "details": { ... }
    },
    "transportation": {
      "score": 7,
      "label": "Giao thong",
      "highlights": [ ... ],
      "details": { ... }
    },
    "street_atmosphere": {
      "score": 9,
      "label": "Duong pho & Ve sinh",
      "highlights": [
        "Hem yeu tinh, it xe qua lai",
        "Sach se, nha cua duoc tu sua tot"
      ],
      "details": { ... }
    },
    "security": {
      "score": 8,
      "label": "An ninh",
      "highlights": [
        "Khu dan cu on dinh",
        "Hem co cong, bao ve"
      ],
      "details": { ... }
    }
  }
}
```

### 5.3 Listings Table Changes

Add column:
```sql
ALTER TABLE listings ADD COLUMN research_id TEXT REFERENCES area_research(id);
```

This links a listing to its most recent research. The `stage` column gains the new `"researching"` value.

---

## 6. API Endpoints

### 6.1 Trigger Batch Research

```
POST /api/v1/campaigns/{campaign_id}/research
```

**Request:**
```json
{
  "listing_ids": ["abc123", "def456", "ghi789"],
  "criteria": [
    "food_shopping",
    "healthcare",
    "education_family",
    "transportation",
    "street_atmosphere",
    "security"
  ],
  "auto_outreach": {
    "enabled": false,
    "threshold": 7.0,
    "must_pass": {
      "security": 6,
      "transportation": 5
    },
    "message_template": "Xin chao anh/chi {landlord_name}..."
  }
}
```

**Response:**
```json
{
  "research_ids": ["res001", "res002", "res003"],
  "status": "queued",
  "message": "3 listings queued for area research"
}
```

### 6.2 Get Research Status / Results

```
GET /api/v1/campaigns/{campaign_id}/research/{research_id}
```

**Response:** Full `area_research` row with parsed JSON fields.

### 6.3 List Research for Campaign

```
GET /api/v1/campaigns/{campaign_id}/research?status=done
```

### 6.4 Research Progress SSE Stream

```
GET /api/v1/campaigns/{campaign_id}/research/stream
```

Streams events for all active research jobs in the campaign:
```json
{"type": "started", "research_id": "res001", "listing_id": "abc123", "address": "..."}
{"type": "progress", "research_id": "res001", "step": "searching_amenities", "detail": "..."}
{"type": "progress", "research_id": "res001", "step": "street_view_walk", "detail": "..."}
{"type": "completed", "research_id": "res001", "overall_score": 8.2, "verdict": "..."}
{"type": "auto_outreach", "research_id": "res001", "listing_id": "abc123", "sent": true}
{"type": "failed", "research_id": "res002", "error": "Address not found on Google Maps"}
{"type": "done"}
```

### 6.5 Retry Failed Research

```
POST /api/v1/campaigns/{campaign_id}/research/{research_id}/retry
```

---

## 7. Backend: TinyFish Agent Workflow

### 7.1 Research Pipeline (per listing)

```
Input: listing.address
   |
   v
[1. Open Google Maps] --> search address
   |
   v
[2. Verify Location] --> confirm pin matches address
   |
   v
[3. Search Amenities] --> for each enabled criterion:
   |   - "restaurants near {address}"
   |   - "hospitals near {address}"
   |   - "schools near {address}"
   |   - "bus stops near {address}"
   |   - etc.
   v
[4. Street View Walk] --> drop into Street View at the address
   |   - Capture 3-5 screenshots (front, left, right, alley entrance)
   |   - Assess street width, cleanliness, lighting, building condition
   v
[5. Synthesize] --> LLM processes raw findings into structured scores
   |
   v
[6. Score & Verdict] --> return ResearchResult
```

### 7.2 TinyFish Goals (new)

A new goal set for Google Maps research, defined in `prompts.py`:

```python
GOAL_AREA_RESEARCH = """
Navigate to Google Maps. Search for the address: {address}.
Verify the location pin is correct.

For each of the following criteria, search "nearby" and collect results:
{criteria_instructions}

Then enter Street View at the address pin.
Look around 360 degrees. Walk 50-100m in each accessible direction.
Describe: street width, surface condition, cleanliness, building facades,
greenery, lighting fixtures, security features (gates, cameras, guards).

Capture screenshots of the Street View at key angles.
"""
```

### 7.3 Scoring Logic

Scoring is done by the LLM (via the main Langclaw agent, not TinyFish) after TinyFish returns raw observations. The LLM receives:
- Raw TinyFish output (amenity lists, Street View descriptions, screenshots)
- A scoring rubric prompt

**Scoring Rubric (per criterion, 1-10):**

| Score | Meaning |
|-------|---------|
| 1-2 | Nothing available / Dangerous / Very poor |
| 3-4 | Very limited options, far away (> 2km) |
| 5-6 | Basic options available within 1km |
| 7-8 | Good variety, walkable (< 500m), reliable |
| 9-10 | Excellent — abundant, diverse, very close |

**Overall score** = weighted average (all criteria equal weight by default).

---

## 8. Frontend Components

### 8.1 New Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `research-action-bar.tsx` | `components/dashboard/` | Floating batch action bar when cards are selected |
| `research-config-sheet.tsx` | `components/dashboard/` | Bottom sheet for criteria + auto-outreach config |
| `research-progress.tsx` | `components/dashboard/` | In-card progress indicator (bar/status) |
| `research-results.tsx` | `components/dashboard/` | Full results panel (overview + details + street view tabs) |
| `score-badge.tsx` | `components/dashboard/` | Reusable colored score display (e.g., "8.2/10") |
| `criteria-scores.tsx` | `components/dashboard/` | Grid of per-criteria score bars |

### 8.2 Modified Components

| Component | Changes |
|-----------|---------|
| `types/index.ts` | Add `"researching"` to `PipelineStage`, add `AreaResearch` interface, add `ResearchCriteria` type |
| `pipeline.tsx` | Render new column |
| `pipeline-column.tsx` | Support checkbox selection mode for "new" column |
| `listing-card.tsx` | Add checkbox (when in selection mode), show research status/score badge |
| `listing-detail.tsx` | Add research results tabs when `research_id` exists |
| `listing-store.ts` | Add selection state, research actions, SSE subscription |
| `api.ts` | Add research API calls |

### 8.3 New Store: `research-store.ts`

```typescript
interface ResearchState {
  // Selection
  selectedListingIds: Set<string>;
  toggleSelection: (id: string) => void;
  selectAll: (ids: string[]) => void;
  clearSelection: () => void;

  // Config (for the sheet)
  criteria: ResearchCriteria[];
  autoOutreach: AutoOutreachConfig;
  setCriteria: (criteria: ResearchCriteria[]) => void;
  setAutoOutreach: (config: AutoOutreachConfig) => void;

  // Active research tracking
  activeResearch: Map<string, ResearchProgress>;  // research_id -> progress
  startResearch: (campaignId: string, listingIds: string[], config: ResearchConfig) => Promise<void>;
  subscribeToProgress: (campaignId: string) => void;

  // Results
  getResult: (researchId: string) => AreaResearchResult | null;
}
```

---

## 9. User Flows

### 9.1 Basic Research Flow

1. User opens the pipeline, sees new listings in "Moi".
2. User taps the checkbox on 3 listing cards.
3. Floating action bar appears: "3 selected | [Khao sat khu vuc] | [Bo qua]"
4. User taps "Khao sat khu vuc".
5. Research config sheet slides up. All criteria pre-checked. Auto-outreach OFF.
6. User unchecks "Giai tri & The thao" (doesn't care about entertainment).
7. User taps "Bat dau khao sat".
8. 3 listings move from "Moi" to "Dang khao sat" column with "Cho xu ly" status.
9. Progress events stream in. Cards update one-by-one: queued -> running -> done.
10. User clicks a completed card. Results panel shows overview with scores.
11. User sees 8.2/10. Clicks "Lien he ngay" -> moves to "Da lien he".

### 9.2 Auto-Outreach Flow

1. Steps 1-5 same as above.
2. User toggles auto-outreach ON.
3. Sets threshold to 7.5. Checks must-pass: Security >= 6.
4. Edits message template or clicks "Tao mau moi voi AI".
5. Taps "Bat dau khao sat".
6. Research runs. Listing A scores 8.2 (security: 8) -> passes -> auto-sends message, moves to "Da lien he". Toast: "Da gui tin nhan cho Anh Minh".
7. Listing B scores 6.1 (security: 4) -> fails must-pass -> stays in "Dang khao sat" with "Khong dat nguong" label. User can review and manually contact.
8. Listing C scores 7.8 (security: 7) -> passes -> auto-sends.

### 9.3 Retry Failed Research

1. Listing shows red "Loi" status in "Dang khao sat" column.
2. User clicks the listing. Detail panel shows error: "Khong tim thay dia chi tren Google Maps".
3. User clicks "Khao sat lai" to retry.
4. Alternatively, user can edit the listing address first, then retry.

---

## 10. Edge Cases

| Case | Handling |
|------|----------|
| Address is null/empty | Skip research, return error: "Khong co dia chi" |
| Address not found on Maps | Mark failed, suggest user verify/edit address |
| Street View unavailable | Research still runs (amenity search only), Street View tab shows "Khong kha dung" with Maps link |
| TinyFish timeout (> 5 min per listing) | Mark failed with timeout error, auto-retry once |
| Duplicate research request | If listing has `status=running` research, reject with message |
| Landlord has no phone/Zalo | Auto-outreach skipped for that listing, logged as "Khong co thong tin lien he" |
| User navigates away during research | Research continues in background. Results available when user returns |
| 50+ listings selected | Warn user about processing time. Queue in batches of 5. |

---

## 11. Metrics

| Metric | How |
|--------|-----|
| Research completion rate | `done / (done + failed)` per campaign |
| Average research time | `completed_at - started_at` |
| Auto-outreach trigger rate | `auto_outreach_triggered / total_done` |
| Score distribution | Histogram of `overall_score` |
| User override rate | Manual contact after failing threshold |
| Criteria usage | Which criteria are most/least checked |

---

## 12. Phased Delivery

### Phase 1 — Core Research (MVP)
- New `"researching"` pipeline stage
- Checkbox selection on "Moi" cards
- Floating action bar with "Khao sat khu vuc" button
- Basic criteria selection (all-or-nothing, no per-criteria toggle yet)
- TinyFish Google Maps integration (amenity search + Street View)
- `area_research` table + API endpoints
- Results panel with overview scores + detail accordion
- SSE progress streaming
- **No auto-outreach yet**

### Phase 2 — Live Preview & Kanban Polish

#### 2.1 Kanban Board UI Improvements

Small but high-value visual tweaks to make the board feel more production-ready:

- **Column header counts** — show a pill badge `(n)` next to each column label that updates live as cards move between stages.
- **Empty-column placeholders** — when a stage has zero listings, render a subtle dashed border + ghost text (e.g., "Chưa có căn nào") instead of blank space.
- **Card image aspect ratio** — enforce a fixed `4:3` thumbnail on all cards so the column height stays predictable; broken images fall back to a grey placeholder with the expand icon.
- **Truncation safety** — price and title overflow should ellipsis at one line; tag chips (`NT`, `BDS`, `FB`, `Zalo`) should never wrap to a second row and instead show `+n` overflow badge.
- **"Đang khao sat" column accent** — the column header gets a teal-500 left-border accent and the column background shifts to `teal-50/30` to visually separate it from the other stages.
- **Card drag handle** (future-proof) — add an invisible drag handle region at the top of each card that shows on hover, stubbed out with `cursor-grab` for future DnD support.

#### 2.2 Live Agent Preview Iframe Inside the Listing Card

When a listing enters `status = "running"`, expand the card in the "Đang khao sat" column to reveal a live iframe feed of the TinyFish agent browsing Google Maps — mirroring the pattern already used in `ScanProgressPanel` for the rental-scan flow (`scan-progress-panel.tsx` / `scan-stream-store.ts`).

**SSE payload extension (backend)**

Add a `browser_url` field to `progress` events already emitted on the research stream:

```json
{
  "type": "progress",
  "research_id": "res001",
  "listing_id": "abc123",
  "step": "searching_amenities",
  "detail": "Searching for restaurants near 280 Bui Huu Nghia...",
  "browser_url": "http://localhost:9222/devtools/inspector.html?ws=..."
}
```

The `browser_url` is the Chrome DevTools Protocol (CDP) live-preview URL that TinyFish exposes per job — identical to the `streaming_url` pattern already used in the scan broker.

**Store extension (`research-store.ts`)**

```typescript
interface ResearchProgress {
  // ... existing fields ...
  browserUrl: string | null;    // live CDP preview URL when running
  currentStep: string | null;   // e.g., "searching_amenities"
  currentDetail: string | null;
}
```

`updateFromSSE` populates `browserUrl` from `progress.browser_url` and clears it on `completed` / `failed`.

**Card UI — expanded running state**

When `researching[researchId].status === "running"` and `browserUrl` is set, the listing card in the "Đang khao sat" column expands from its compact form to show:

```
+--------------------------------------------------+
| [thumbnail]  2PN Nguyen Huu Canh · 8tr/th       |
|              Binh Thanh · 1PN · 45m²            |
+--------------------------------------------------+
|  ● Đang khao sat  Đang tim kiem tien ich...      |  <- ticking step label
+--------------------------------------------------+
|                                                  |
|  +--------------------------------------------+ |
|  |                                            | |
|  |         [live iframe — CDP preview]        | |
|  |         h-40  (160px), rounded-md          | |
|  |                                            | |
|  +--------------------------------------------+ |
+--------------------------------------------------+
```

- `iframe` height is `h-40` (160 px) — compact enough to keep multiple running cards visible in the column scroll area.
- `sandbox="allow-same-origin allow-scripts"` — matches the existing scan preview policy in `ScanProgressPanel`.
- The iframe is only rendered when `browserUrl != null`; while `browserUrl` is null but `status === "running"`, show a `w-full h-40 bg-muted/50 animate-pulse rounded-md` skeleton.
- Cards that are `queued` or `done` remain compact (no iframe).

**New sub-component: `ResearchLivePreview`**

```
components/dashboard/research-live-preview.tsx
```

```tsx
interface ResearchLivePreviewProps {
  browserUrl: string | null;
  currentDetail: string | null;
}
```

Renders the iframe + step label. Used inside `listing-card.tsx` for the expanded running state and also inside `research-progress.tsx`.

**Modified files:**

| File | Change |
|------|--------|
| `api/research_broker.py` | Expose `browser_url` from TinyFish CDP port in progress callbacks |
| `api/routes/research.py` | Forward `browser_url` in SSE `progress` events |
| `stores/research-store.ts` | Add `browserUrl`, `currentStep`, `currentDetail` to `ResearchProgress` |
| `hooks/use-research-stream.ts` | Parse and store `browser_url` from progress events |
| `components/dashboard/listing-card.tsx` | Conditionally expand card + render `<ResearchLivePreview>` |
| `components/dashboard/research-live-preview.tsx` | **New** — iframe + skeleton + step label |
| `types/index.ts` | Add `browser_url?: string` to `ResearchSSEEvent` progress variant |

#### 2.3 Ticking "Research Running" Indicator

A small, unobtrusive signal visible at a glance that at least one research job is active. Three locations:

**a) Column header pulse dot**

The "Đang khao sat" column header shows a pulsing teal dot next to the count badge when any card in the column has `status === "running"`:

```
● Đang khao sat (3)   <-- dot pulses via Tailwind animate-pulse
```

`pipeline-column.tsx` receives a boolean `hasRunning` prop; when true, prepend a `<span className="h-2 w-2 rounded-full bg-teal-500 animate-pulse" />` before the title text.

**b) In-card step ticker**

Inside each running card (above the iframe), a one-line row shows:

```
[● ping dot]  Đang tim kiem tien ich gan 280 Bui Huu Nghia...
```

- The dot is `h-1.5 w-1.5 rounded-full bg-teal-500 animate-ping`.
- The step text is `currentDetail` from the store, truncated at 60 chars with a CSS `truncate`.
- Text color: `text-teal-700 dark:text-teal-400`, size `text-xs`.

**c) Dashboard top-bar badge**

When `hasActiveResearch` is true in `dashboard.tsx`, show a subtle pill in the top bar next to the campaign name:

```
[● Đang nghiên cứu (2)]
```

- Pill: `bg-teal-100 text-teal-800 border border-teal-300 rounded-full px-2 py-0.5 text-xs`.
- Contains a `animate-pulse` dot + count of currently `running` jobs.
- Disappears automatically when count drops to zero.

### Phase 3 — Auto-Outreach
- Auto-outreach toggle + threshold config in research sheet
- Must-pass conditions
- Message template editor + AI generation
- Auto-send via Zalo integration
- Toast notifications for auto-sent messages
- Activity log entries

### Phase 4 — Polish
- Street View screenshot gallery tab
- Research comparison view (compare 2-3 listings side-by-side)
- Save/reuse research config presets
- Re-research with different criteria
- Export research report (PDF)

---

## 13. Open Questions

1. **Concurrency limit:** How many TinyFish agents can run simultaneously? This determines batch size.
2. **Cost:** TinyFish API cost per research job? Impacts whether we warn users before large batches.
3. **Caching:** If two listings share the same address/alley, should we reuse research results?
4. **Score weights:** Should users be able to customize criterion weights for the overall score?
5. **Zalo rate limits:** How many auto-outreach messages can we send per hour before triggering Zalo's anti-spam?

# PRD-06: Onboarding Screen Refactor — Chat-First Experience

**Status:** Ready to build
**Deadline:** 1 day
**Stack:** Next.js 16 / React 19 / TypeScript / Tailwind 4 / Zustand 5
**Audience:** Solo dev + Claude Code agents

---

## 1. Overview

### Problem

The current `SetupWizard` implementation is a generic form wizard that doesn't match the product's identity:

1. **Language mismatch**: All copy is in English but target users are Vietnamese Gen Z/millennials who expect Vietnamese UI
2. **Design system violation**: Uses generic shadcn tokens (`bg-muted`, `bg-primary`, `text-muted-foreground`) instead of the warm cream palette (`--cream`, `--terra`, `--ink`)
3. **Visual disconnect**: Card-based layout centered on screen feels like an admin form — not "a friend texting you apartment recommendations"
4. **Step indicator**: Generic numbered circles don't reinforce the product's signature
5. **Mobile-first failure**: Centered `max-w-2xl` card wastes mobile viewport space; CTAs not thumb-reachable
6. **Flow friction**: 4 discrete card-based steps feel transactional rather than conversational

### Goal

Transform onboarding from "form wizard" to **chat-first conversational flow**:

- Full-screen steps with warm cream background
- Chat-first preference extraction in Vietnamese
- Mobile-optimized layouts with bottom-anchored CTAs
- Visual alignment with the design system established in PRD-05

### Success Criteria

- A user can complete onboarding in under 3 minutes on mobile
- All UI copy is in natural Vietnamese (matching the tone in RENTAGENT.md)
- Visual tokens match `.interface-design/system.md` exactly
- CTAs are thumb-reachable at 390px viewport width
- Chat step feels conversational, not form-like

---

## 2. Design Reference

| Artifact | Path | Purpose |
|---|---|---|
| Design system | `.interface-design/system.md` | All tokens, component patterns, spacing scale |
| Product spec | `examples/rentagent_vn/RENTAGENT.md` Section 5.1 | Onboarding flow requirements |
| Mobile UX patterns | `docs/PRD-05-mobile-ux-refactor.md` | Reference for mobile-first patterns |

**All visual decisions are already made.** Token names in this PRD (e.g. `--terra`, `--ink-30`) reference `system.md` exactly.

---

## 3. What's Changing

| Area | Before | After |
|---|---|---|
| Root layout | Centered `max-w-2xl` Card | Full-screen `bg: --cream`, no card wrapper |
| Step indicator | Numbered circles (1-2-3-4) | Minimal dot progress bar |
| Chat UI | Generic chat bubbles with `bg-muted` | Warm bubbles: user `--terra`, AI `--white` with shadow |
| All copy | English | Vietnamese |
| CTAs | Standard buttons at bottom of Card | Bottom-anchored, full-width on mobile, `--terra` accent |
| Typography | Default shadcn | Inter with system weight scale |
| Sources step | Static default list | District-aware suggestions based on Step 2 |

---

## 4. Screen Specs

### 4.1 Setup Wizard Shell (`setup-wizard.tsx`)

**Layout:** Full-screen, `min-h-screen`, `bg: --cream`

```
flex-col, min-h-screen
├── ProgressDots        fixed top, center, z-10
└── [active step]       flex-1
```

**ProgressDots:**
- 4 dots, horizontally centered
- Active dot: `--terra`, 8px diameter
- Completed dot: `--terra` at 50% opacity, 8px diameter
- Upcoming dot: `--ink-15`, 6px diameter
- Gap between dots: 8px
- Position: `top: 16px`, centered horizontally
- Container: `padding: 8px 16px`, `bg: rgba(250,247,242,.9)`, `backdrop-blur(8px)`, `border-radius: --r-full`

**Remove:** The current `min-h-screen flex items-center justify-center bg-background p-4` wrapper and `max-w-2xl` constraint.

---

### 4.2 Chat Step (`chat-step.tsx`)

The primary onboarding experience. User describes their needs in natural Vietnamese; AI extracts structured preferences.

**Layout:** `flex-col, h-screen, bg: --cream`

```
ChatHeader           flex-shrink: 0, padding: 60px 20px 16px
ChatMessages         flex: 1, overflow-y: auto, padding: 0 20px
ChatInput            flex-shrink: 0, padding: 16px 20px 32px, bg: --cream
```

#### ChatHeader

- Title: "Chào bạn! 👋" — 22px/800, `--ink`
- Subtitle: "Mô tả phòng bạn đang tìm, mình sẽ giúp bạn tìm nhanh hơn." — 14px/500, `--ink-50`

#### ChatMessages

**AI message bubble:**
- Background: `--white`
- Border: `1px solid --ink-08`
- Shadow: `--shadow-card` (from system.md)
- Border-radius: `20px 20px 20px 6px` (tail bottom-left)
- Padding: `12px 16px`
- Max-width: `85%`
- Text: 14px/500, `--ink`
- Align: left

**User message bubble:**
- Background: `--terra`
- Border: none
- Border-radius: `20px 20px 6px 20px` (tail bottom-right)
- Padding: `12px 16px`
- Max-width: `85%`
- Text: 14px/500, white
- Align: right

**System message (tool progress):**
- No bubble, inline text
- Text: 12px/500, `--ink-30`, italic
- Icon: small spinner or `...` animation

**Typing indicator:**
- Three dots with staggered pulse animation
- Inside AI bubble shape
- `--ink-30` color

**Initial AI message:**
```
"Mình sẽ giúp bạn tìm phòng trọ! Bạn muốn tìm ở khu vực nào, giá tầm bao nhiêu, mấy phòng ngủ?"
```

#### ChatInput

- Container: `bg: --white`, `border: 1px solid --ink-15`, `border-radius: --r-lg` (20px)
- Input field: no border, transparent bg, placeholder `--ink-30`
- Placeholder: "Ví dụ: Phòng trọ Bình Thạnh, dưới 8 triệu..."
- Send button: 40px circle, `--terra` bg when input has text, `--ink-08` bg when empty
- Send icon: Arrow-up or Send icon, white when active

**Skip link:**
- Below input: "Bỏ qua, nhập thủ công →"
- Text: 12px/500, `--ink-30`, underline on hover
- Tap: calls `onExtracted({})` to proceed with empty preferences

#### Preference Extraction

When AI has gathered enough information, it responds with a summary and JSON block. The component detects the JSON and auto-advances after 1.5s delay:

```
"Mình hiểu rồi! Bạn đang tìm:

• Khu vực: Bình Thạnh, Phú Nhuận
• Ngân sách: 6–8 triệu/tháng
• Loại: 1 phòng ngủ
• Yêu cầu: Có chỗ để xe máy

Đúng chưa? Mình sẽ chuyển sang bước tiếp theo..."

```json
{"district":"Bình Thạnh, Phú Nhuận","min_price":6000000,"max_price":8000000,"bedrooms":1,"notes":"Có chỗ để xe máy"}
```
```

---

### 4.3 Confirm Step (`confirm-step.tsx`)

Review and edit extracted preferences before proceeding.

**Layout:** `flex-col, min-h-screen, bg: --cream`

```
ConfirmHeader        padding: 60px 20px 24px
PreferenceTags       flex-1, padding: 0 20px
EditFields           conditional, padding: 0 20px
ConfirmFooter        padding: 16px 20px 32px
```

#### ConfirmHeader

- Back button: top-left, ghost style, `← Quay lại`
- Title: "Xác nhận tiêu chí" — 22px/800, `--ink`
- Subtitle: "Chạm vào để chỉnh sửa" — 13px/500, `--ink-50`

#### PreferenceTags

Editable tag pills for each filled preference. Tap to edit inline.

**Tag anatomy:**
- Container: `bg: --white`, `border: 1px solid --ink-08`, `border-radius: --r-full`, padding `8px 16px`
- Label: 11px/600, `--ink-30`, uppercase, `letter-spacing: 0.5px`
- Value: 14px/600, `--ink`
- Edit icon: Pencil, 14px, `--ink-30`, right side
- Active state (editing): `border: 2px solid --terra`, `bg: --terra-08`

**Tag layout:**
- Flex wrap, gap: 10px
- Tags for: Khu vực, Ngân sách, Phòng ngủ, Diện tích, Ghi chú

**Empty tag (field not extracted):**
- Dashed border: `border: 1px dashed --ink-15`
- Text: "+ Thêm {field name}"
- Tap: shows inline input

#### EditFields

When a tag is tapped, show inline edit field below the tags section:

- Label: 11px/600, `--ink-30`, uppercase
- Input: full-width, `bg: --white`, `border: 1px solid --ink-15`, `border-radius: --r-sm`, padding `12px 16px`
- Input text: 14px/500, `--ink`
- Keyboard: numeric for price/area/bedrooms fields

#### ConfirmFooter

- Primary CTA: "Tiếp tục →" — full-width, `bg: --terra`, white text, `border-radius: --r-lg`, height 52px, 15px/600
- Secondary: Back button handled in header

#### Field Labels (Vietnamese)

| Field key | Label | Placeholder |
|---|---|---|
| `district` | Khu vực | Quận 7, Bình Thạnh... |
| `property_type` | Loại hình | Phòng trọ, căn hộ mini... |
| `bedrooms` | Phòng ngủ | 1, 2, 3... |
| `min_price` | Giá tối thiểu | 5,000,000 |
| `max_price` | Giá tối đa | 10,000,000 |
| `min_area` | Diện tích tối thiểu | 25 m² |
| `notes` | Yêu cầu khác | Có ban công, gần metro... |

---

### 4.4 Sources Step (`sources-step.tsx`)

Select which Facebook/Zalo groups and websites to scan.

**Layout:** `flex-col, min-h-screen, bg: --cream`

```
SourcesHeader        padding: 60px 20px 24px
SuggestedSources     padding: 0 20px, margin-bottom: 24px
CustomSources        flex-1, padding: 0 20px
SourcesFooter        padding: 16px 20px 32px
```

#### SourcesHeader

- Back button: top-left, ghost
- Title: "Chọn nguồn tìm kiếm" — 22px/800, `--ink`
- Subtitle: "Mình sẽ quét các trang này để tìm phòng cho bạn" — 13px/500, `--ink-50`

#### SuggestedSources

**Section label:** "Nguồn đề xuất" — 11px/600, `--ink-30`, uppercase, `letter-spacing: 0.8px`, margin-bottom 12px

**Source card anatomy:**
- Container: `bg: --white`, `border: 1px solid --ink-08`, `border-radius: --r-lg`, padding `14px 16px`
- Row layout: Icon (36x36 container) + Content + Toggle
- Icon container: `border-radius: --r-sm`, platform-specific bg color
- Platform icon: 20px, centered
- Content: Platform name (13px/600, `--ink`) + URL preview (12px/400, `--ink-30`, truncated)
- Toggle: 44x26px, same style as Settings screen toggles

**Platform icon colors:**
- Nhà Tốt: `#F57C00` bg (orange)
- Batdongsan: `#1976D2` bg (blue)
- Facebook: `#1877F2` bg
- Zalo: `#0068FF` bg

**Default sources:**
```typescript
const DEFAULT_SOURCES = [
  { url: "https://www.nhatot.com/thue-phong-tro", label: "Nhà Tốt", platform: "nhatot", enabled: true },
  { url: "https://batdongsan.com.vn/cho-thue", label: "Batdongsan.com.vn", platform: "bds", enabled: true },
];
```

**District-aware suggestions:**
If `preferences.district` contains known districts, show relevant Facebook groups:

```typescript
const DISTRICT_GROUPS: Record<string, { url: string; label: string }[]> = {
  "Bình Thạnh": [
    { url: "https://facebook.com/groups/phongtrobinhthanh", label: "Phòng Trọ Bình Thạnh" },
  ],
  "Quận 7": [
    { url: "https://facebook.com/groups/phongtroquan7", label: "Phòng Trọ Quận 7" },
  ],
  // ... etc
};
```

Show these with Facebook icon and a "Đề xuất dựa trên khu vực bạn chọn" label.

#### CustomSources

**Section label:** "Thêm nguồn khác" — 11px/600, `--ink-30`, uppercase

**Add URL input:**
- Container: `bg: --white`, `border: 1px solid --ink-15`, `border-radius: --r-lg`, padding `12px 16px`
- Flex row: Input (flex-1) + Add button (40px circle)
- Input placeholder: "Dán link nhóm Facebook, Zalo..."
- Add button: `--terra` bg when valid URL, `--ink-08` when empty, Plus icon

**Added custom sources:**
- Same card style as suggested sources
- X button to remove instead of toggle

**Error state:**
- Text below input: "Link không hợp lệ" — 12px/500, `#C03` (destructive)

#### SourcesFooter

- Primary CTA: "Tiếp tục → ({n} nguồn)" — includes count of enabled sources
- Disabled state: when 0 sources enabled, button is `--ink-15` bg, `--ink-30` text

---

### 4.5 Frequency Step (`frequency-step.tsx`)

Select scan frequency and launch the campaign.

**Layout:** `flex-col, min-h-screen, bg: --cream`

```
FrequencyHeader      padding: 60px 20px 24px
FrequencyOptions     flex-1, padding: 0 20px
LaunchFooter         padding: 16px 20px 32px
```

#### FrequencyHeader

- Back button: top-left, ghost
- Title: "Lịch quét tự động" — 22px/800, `--ink`
- Subtitle: "Bạn luôn có thể quét thủ công bất cứ lúc nào" — 13px/500, `--ink-50`

#### FrequencyOptions

Radio-style selection cards. Only one can be selected.

**Option card anatomy:**
- Container: `bg: --white`, `border: 1px solid --ink-08`, `border-radius: --r-lg`, padding `16px`
- Selected state: `border: 2px solid --terra`, `bg: --terra-08`
- Row layout: Radio indicator + Content
- Radio indicator: 20px circle, `--ink-15` border when unselected, `--terra` fill when selected
- Title: 14px/600, `--ink`
- Description: 12px/400, `--ink-50`

**Options:**

```typescript
const FREQUENCIES = [
  {
    value: "manual",
    title: "Thủ công",
    description: "Quét khi bạn bấm nút. Phù hợp nếu không vội.",
  },
  {
    value: "1x_day",
    title: "Mỗi ngày",
    description: "Tự động quét lúc 8:00 sáng mỗi ngày.",
    recommended: true,
  },
  {
    value: "2x_day",
    title: "2 lần/ngày",
    description: "Quét lúc 8:00 sáng và 6:00 chiều. Không bỏ lỡ tin mới.",
  },
];
```

**Recommended badge:**
- On "Mỗi ngày" option: small pill "Đề xuất" — `--jade-15` bg, `--jade` text, 10px/600

#### LaunchFooter

**Primary CTA:** "Bắt đầu tìm kiếm 🚀"
- Full-width, `bg: --terra`, white text
- `border-radius: --r-lg`, height 56px (slightly taller for emphasis)
- Text: 16px/700
- Loading state: "Đang tạo..." with pulse animation

**Trust signal (optional):**
- Below button: "Mình sẽ bắt đầu quét ngay sau khi tạo xong" — 12px/400, `--ink-30`, centered

---

## 5. Component Token Reference

All components should use these CSS custom properties (defined in system.md):

```css
/* Backgrounds */
--cream: #FAF7F2;
--cream-100: #F3EDE2;
--white: #FFFFFF;

/* Text */
--ink: #1A1815;
--ink-70: rgba(26,24,21,.70);
--ink-50: rgba(26,24,21,.50);
--ink-30: rgba(26,24,21,.30);

/* Borders */
--ink-15: rgba(26,24,21,.15);
--ink-08: rgba(26,24,21,.08);

/* Accent */
--terra: #C4562A;
--terra-15: rgba(196,86,42,.15);
--terra-08: rgba(196,86,42,.08);

/* Semantic */
--jade: #3D7A63;
--jade-15: rgba(61,122,99,.15);

/* Shadows */
--shadow-card: 0 2px 8px rgba(26,24,21,.06), 0 8px 32px rgba(26,24,21,.10);

/* Radius */
--r-sm: 10px;
--r-lg: 20px;
--r-full: 999px;

/* Spacing base: 4px */
```

---

## 6. Vietnamese Copy Reference

### Chat Step

| Element | Copy |
|---|---|
| Header title | Chào bạn! 👋 |
| Header subtitle | Mô tả phòng bạn đang tìm, mình sẽ giúp bạn tìm nhanh hơn. |
| Initial AI message | Mình sẽ giúp bạn tìm phòng trọ! Bạn muốn tìm ở khu vực nào, giá tầm bao nhiêu, mấy phòng ngủ? |
| Input placeholder | Ví dụ: Phòng trọ Bình Thạnh, dưới 8 triệu... |
| Skip link | Bỏ qua, nhập thủ công → |
| Typing indicator | Đang suy nghĩ... |

### Confirm Step

| Element | Copy |
|---|---|
| Title | Xác nhận tiêu chí |
| Subtitle | Chạm vào để chỉnh sửa |
| Back button | ← Quay lại |
| CTA | Tiếp tục → |
| Empty tag | + Thêm {field} |

### Sources Step

| Element | Copy |
|---|---|
| Title | Chọn nguồn tìm kiếm |
| Subtitle | Mình sẽ quét các trang này để tìm phòng cho bạn |
| Suggested section | NGUỒN ĐỀ XUẤT |
| Custom section | THÊM NGUỒN KHÁC |
| Input placeholder | Dán link nhóm Facebook, Zalo... |
| CTA | Tiếp tục → ({n} nguồn) |
| Error | Link không hợp lệ |
| Zero sources | Chọn ít nhất 1 nguồn để tiếp tục |

### Frequency Step

| Element | Copy |
|---|---|
| Title | Lịch quét tự động |
| Subtitle | Bạn luôn có thể quét thủ công bất cứ lúc nào |
| Manual option | Thủ công / Quét khi bạn bấm nút. Phù hợp nếu không vội. |
| Daily option | Mỗi ngày / Tự động quét lúc 8:00 sáng mỗi ngày. |
| 2x option | 2 lần/ngày / Quét lúc 8:00 sáng và 6:00 chiều. Không bỏ lỡ tin mới. |
| Recommended badge | Đề xuất |
| CTA | Bắt đầu tìm kiếm 🚀 |
| Loading | Đang tạo... |
| Trust signal | Mình sẽ bắt đầu quét ngay sau khi tạo xong |

---

## 7. Out of Scope

Do not build these now:

| Feature | Why deferred |
|---|---|
| Zalo connection in onboarding | PRD-02 handles this separately post-onboarding |
| Voice input | Requires additional dependencies |
| Animated transitions between steps | Nice-to-have, not blocking |
| District autocomplete | Can use free-text for v1 |
| Source activity indicators | Requires backend work |

---

## 8. Build Sequence

### Step 1 — Setup wizard shell + progress dots (~30 min)

Update `setup-wizard.tsx`:
- Remove Card wrapper, centered layout
- Add full-screen `bg-[#FAF7F2]` (or CSS var)
- Implement `ProgressDots` component at top
- Test step transitions work

**Ship check:** Wizard loads with cream background and dot indicators.

### Step 2 — Chat step redesign (~1.5 hrs)

Update `chat-step.tsx`:
- Full-height layout with header, messages, input areas
- Implement bubble styles (user: terra, AI: white)
- Vietnamese initial message and placeholder
- Typing indicator with animation
- Skip link at bottom
- Keep existing WebSocket and preference extraction logic

**Ship check:** Chat renders with warm bubbles, Vietnamese copy, sends messages.

### Step 3 — Confirm step redesign (~1 hr)

Update `confirm-step.tsx`:
- Replace Badge chips with tag pills
- Vietnamese labels
- Inline edit on tap
- Bottom-anchored CTA
- Back button in header

**Ship check:** Tags display, edit works, Vietnamese labels throughout.

### Step 4 — Sources step redesign (~1 hr)

Update `sources-step.tsx`:
- Toggle-style source cards
- Platform icons with colored backgrounds
- Custom URL input with validation
- Vietnamese copy
- Count in CTA button

**Ship check:** Sources toggle on/off, custom URLs add/remove, count updates.

### Step 5 — Frequency step redesign (~45 min)

Update `frequency-step.tsx`:
- Radio-style option cards
- Recommended badge on daily option
- Prominent launch CTA with emoji
- Loading state
- Vietnamese copy

**Ship check:** Options select correctly, campaign creates on submit.

### Step 6 — Polish + mobile test (~30 min)

- Test at 390px viewport
- Verify all CTAs are thumb-reachable
- Check typography weights match system
- Verify no English copy remains
- Test full flow end-to-end

---

## Appendix: Key File Paths

```
Frontend root:        examples/rentagent_vn/frontend/
Design system:        .interface-design/system.md
Setup components:     frontend/src/components/setup/
  - setup-wizard.tsx
  - chat-step.tsx
  - confirm-step.tsx
  - sources-step.tsx
  - frequency-step.tsx
```

## Appendix: CSS Token Quick Reference

```css
/* Most-used in onboarding */
--cream: #FAF7F2       /* all backgrounds */
--white: #FFFFFF       /* bubbles, cards, inputs */
--terra: #C4562A       /* user bubbles, CTAs, active states */
--ink:   #1A1815       /* headings, primary text */
--ink-50: rgba(26,24,21,.50)  /* subtitles */
--ink-30: rgba(26,24,21,.30)  /* labels, placeholders */
--ink-15: rgba(26,24,21,.15)  /* borders */
--ink-08: rgba(26,24,21,.08)  /* subtle borders */

--r-lg:   20px    /* cards, inputs */
--r-full: 999px   /* pills, buttons */

--shadow-card: 0 2px 8px rgba(26,24,21,.06), 0 8px 32px rgba(26,24,21,.10);
```

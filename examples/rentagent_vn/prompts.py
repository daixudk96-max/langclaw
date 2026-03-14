"""System prompt, TinyFish goal templates, and default platform URLs."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Default rental platform URLs (used when frontend provides none)
# ---------------------------------------------------------------------------

DEFAULT_PLATFORM_URLS: list[str] = [
    "https://www.nhatot.com/thue-phong-tro",
    "https://batdongsan.com.vn/cho-thue",
]

# ---------------------------------------------------------------------------
# System prompt for the main claw agent
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are an expert rental assistant for the Vietnamese market. You help users \
find apartments, rooms, and houses for rent across Vietnam — primarily in \
Ho Chi Minh City and Hanoi.

### What you can do
- **Search listings** across multiple platforms using the `search_rentals` tool.
- **Research neighbourhoods** using `research_area` (safety, amenities, reviews).
- **Draft landlord messages** via `contact_landlord` (stub — tells the user \
  how to reach the landlord directly with phone/Zalo).
- **Schedule recurring scans** via the built-in cron tool.

### How `search_rentals` works
- You provide a natural-language `query` describing what the user wants.
- The tool automatically searches across all configured platform URLs.
- Keep the query focused: describe the property (area, bedrooms, budget, \
  special requirements) in plain English.
- If the user mentions preferences during conversation (e.g. "I prefer high \
  floors" or "must have a balcony"), pass these as the `user_preference` \
  parameter so results are filtered better.
- **The tool runs in the background** — it returns immediately with a job ID. \
  Results are delivered to this chat automatically when ready (typically \
  3–8 minutes). After calling the tool, let the user know that results \
  are on the way and they can continue chatting in the meantime.

### Vietnamese rental market context
- Prices are in VND per month. Common shorthand:
  - "5 trieu" or "5tr" = 5,000,000 VND/month
  - "15 trieu" = 15,000,000 VND/month
- Deposits are typically 1-3 months rent.
- Major cities: Ho Chi Minh City (Saigon), Hanoi, Da Nang.
- Districts: "Quan 1", "Quan 7", "Binh Thanh", "Thu Duc", "Ba Dinh", etc.
- Common platforms: nhatot.com, batdongsan.com.vn, Facebook rental groups.

### How to present results
- Show a **ranked shortlist** (top 5-8 listings), not a raw data dump.
- For each listing include: title, price, location, size, bedrooms, and \
  landlord contact (phone/Zalo).
- Highlight listings that match the user's stated and inferred preferences.
- If landlord contact info is available, show it directly — the user can \
  reach out via Zalo (https://zalo.me/<phone>) or phone.

### Important
- Do NOT invent or fabricate listings. Only present data returned by tools.
- If no listings match, say so honestly and suggest broadening criteria.
- When the user provides URLs (Facebook groups, forum links), note that \
  those URLs are configured at the platform level — your job is to write \
  a good search query.
"""

# ---------------------------------------------------------------------------
# TinyFish goal templates — used by the scrape workflow to build goals
# per-platform. The {query} and {user_preference} placeholders are filled
# at runtime.
# ---------------------------------------------------------------------------

LISTING_SCHEMA_SAMPLE = """\
## Output format

Return ONLY a JSON object — no markdown fences, no explanation, no extra text.

The top-level key MUST be "listings" (not "rentals", "results", "data", or \
anything else). Use ONLY the exact field names shown below.

Example (one listing):

{{
  "listings": [
    {{
      "title": "2BR with balcony · District 7 · 12M/month",
      "description": "2 bedroom apartment, 1 bathroom, spacious balcony",
      "price_vnd": 12000000.0,
      "price_display": "12M/month",
      "deposit_vnd": 24000000.0,
      "address": "123 Nguyen Huu Tho, District 7, HCMC",
      "district": "District 7",
      "city": "Ho Chi Minh",
      "area_sqm": 65.0,
      "bedrooms": 2,
      "bathrooms": 1,
      "listing_url": "https://example.com/listing/123",
      "thumbnail_url": "https://example.com/actual_room_image.jpg",
      "posted_date": "2026-02-28",
      "source_platform": "nhatot.com",
      "landlord_name": "Mr. Minh",
      "landlord_phone": "0901234567",
      "landlord_zalo": "0901234567",
      "landlord_facebook_url": "https://www.facebook.com/profile.php?id=100001234567",
      "landlord_contact_method": "phone,zalo"
    }}
  ]
}}

Field guide (use these EXACT keys):
- title           : Short headline — room type · district · price \
(e.g. "Studio · Binh Thanh · 4M")
- description     : 1-2 sentence summary (size, furniture, notable features)
- price_vnd       : Monthly rent as float. Convert shorthand: \
5tr = 5000000.0, 15 trieu = 15000000.0. null if unknown
- price_display   : Price as written in the post (e.g. "5M/month")
- deposit_vnd     : Deposit as float. null if not mentioned
- address         : Street address or location description
- district        : District name (e.g. "Binh Thanh", "Quan 7")
- city            : City name, default "Ho Chi Minh"
- area_sqm        : Area in m² as float. null if unknown
- bedrooms        : Number of bedrooms (integer). \
Extract from "1PN"=1, "2PN"=2. null if unknown
- bathrooms       : Number of bathrooms (integer). null if unknown
- listing_url     : Permalink to this specific post or listing page
- thumbnail_url   : Actual high-resolution image of the room/property. \
CRITICAL: Do NOT extract user avatars or tiny UI icons. \
Finding a real photo of the rental is extremely important. null if none exist.
- posted_date     : Date posted (YYYY-MM-DD). null if unknown
- source_platform : "facebook", "nhatot.com", "batdongsan.com.vn", etc.
- landlord_name   : Name of the poster / landlord. null if unknown
- landlord_phone  : Vietnamese mobile (09xx/03xx/07xx/08xx/05xx). null if not found
- landlord_zalo   : Zalo number (often same as phone). null if not found
- landlord_facebook_url   : Facebook profile URL of the poster. null if not available
- landlord_contact_method : Comma-separated — "phone", "zalo", "messenger"

CRITICAL RULES:
- If a value is unknown or not mentioned, set it to null. \
NEVER use placeholder text like "Not mentioned", "Unknown", "N/A", or "Contact".
- Do NOT add extra fields (no "id", "note", "group", "rooms", "contact", \
"location", "area", "price"). Use ONLY the field names listed above.
- Return valid JSON only."""


GOAL_FACEBOOK_GROUP = """\
## Objective
Search for rental listings in this Facebook group using the group's search \
function, then extract matching results.

## Steps
1. **Search within the group.**
   - Locate the search icon or search bar inside the group (usually near the \
top of the group page, labeled "Tìm kiếm trong nhóm" or a magnifying glass icon).
   - Type the search query into the group search box and press Enter.
   - If a sort/filter option appears, select **"Mới nhất" (Newest)** to surface \
the most recent posts first.
   - If the group search is unavailable, fall back to browsing the feed sorted \
by "Mới nhất" — look for a "Sắp xếp" or sort toggle near the top of the feed.

2. **Filter results — accept ONLY valid rental offers.**
   - CRITICAL: STRICTLY IGNORE posts from people looking for rent \
(rentees saying "tìm phòng", "cần tìm", "cần thuê", "ai có phòng không"). \
ONLY extract posts from landlords or agents offering a rental ("cho thuê", \
"pass phòng", "còn phòng trống").
   - Skip discussions, questions, memes, and non-rental content.
   - PRIORITIZE posts from the last 7 days. Deprioritize posts older than 30 days \
(extract them only if you cannot find enough recent ones).

3. **Extract listing details from each valid post.**
   - Read the full post text for price, address, size, room type, and contact info.
   - Prefer posts whose content explicitly matches the search query \
(district, price range, room type).

4. **Capture media and contact.**
   - Locate and extract the actual image of the room attached to the post for \
thumbnail_url (do NOT use the poster's profile picture or group cover photo).
   - Capture the poster's Facebook profile URL as landlord_facebook_url.

## Termination Conditions
Stop when ANY of these is true:
- You have successfully extracted between 5 and 10 valid rental listings \
THAT INCLUDE at least one valid contact method (phone, zalo, or messenger link). \
Do not stop until you have at least 5 with contacts.
- You have reviewed 40 posts from the search results and cannot find more matches.
- No more content loads after scrolling.

## Guardrails
- Do NOT click into individual posts or navigate away from the group feed.
- Do NOT invent or fabricate any data not present in the post.
- Do NOT use the main Facebook search bar — search WITHIN the group only.

## Edge cases
- If a post mentions price in shorthand (e.g. "5tr", "5M"), convert: \
5tr = 5000000.0 for price_vnd, keep "5M/month" for price_display.
- If a post contains multiple units at different prices, create one listing per unit.
- "1PN" means bedrooms=1, "2PN" means bedrooms=2, "Studio" means bedrooms=0.
- Most Facebook posts will NOT have all fields. Set missing fields to null.

## Context
User is looking for: {query}
{preference_line}

{schema_block}"""


GOAL_NHATOT = """\
## Objective
Search for rental listings on this Nha Tot page.

## Steps
1. If there is a search box, type the search query. Otherwise, browse the current listing page.
2. Wait for results to load.
3. Extract the listings from the results page.
4. Ensure you extract the actual property image from the listing card for the thumbnail_url.

## Termination Conditions
Stop when ANY of these is true:
- You have successfully extracted between 5 and 10 valid rental listings \
THAT INCLUDE at least one contact method (phone, zalo, or chat). \
Do not stop until you have at least 5 with contacts.
- You reach the end of the results page.

## Guardrails
- Do NOT click on individual listings — extract from the results page only.
- Set source_platform to "nhatot.com" for all listings.

## Context
User is looking for: {query}
{preference_line}

{schema_block}"""


GOAL_BATDONGSAN = """\
## Objective
Search for rental listings on this Bat Dong San page.

## Steps
1. If there is a search/filter interface, use it to narrow down results.
2. Wait for results to load.
3. Extract the listings from the results page.
4. Ensure you extract the actual property image from the listing card for the thumbnail_url.

## Termination Conditions
Stop when ANY of these is true:
- You have successfully extracted between 5 and 10 valid rental listings \
THAT INCLUDE at least one contact method (phone, zalo, or chat). \
Do not stop until you have at least 5 with contacts.
- You reach the end of the results page.

## Guardrails
- Set source_platform to "batdongsan.com.vn" for all listings.

## Context
User is looking for: {query}
{preference_line}

{schema_block}"""


GOAL_GENERIC = """\
## Objective
Extract rental listings from this webpage.

## Steps
1. Scroll down to load more content if the page uses infinite scroll.
2. Look for rental property listings.
3. Ensure you extract the actual property image from the listing for the thumbnail_url, \
not site logos or tiny icons.

## Termination Conditions
Stop when ANY of these is true:
- You have successfully extracted between 5 and 10 valid rental listings \
THAT INCLUDE at least one contact method. Do not stop until you have at least 5 with contacts.
- You reach the end of the page or no more items load.

## Guardrails
- Do NOT add extra fields not listed in the schema below.

## Context
User is looking for: {query}
{preference_line}

{schema_block}"""


# ---------------------------------------------------------------------------
# Outreach message drafting prompt
# ---------------------------------------------------------------------------

OUTREACH_DRAFT_PROMPT = """\
You are a proactive and friendly prospective tenant looking for a rental in Vietnam.
Your goal is to write a natural, concise Zalo message to a landlord or agent.

## Instructions
1. **Analyze the Information**: Review the provided listing details.
2. **Determine the Intent**:
    - **Scenario A (Missing Info):** If key details are missing (e.g., no price,
      no mention of photos, or vague location), prioritize asking for that info.
    - **Scenario B (Sufficient Info):** If details are clear and complete, skip
      the questions and ask for a specific time to visit and see the property.
3. **Tone & Style**:
    - Write 2-3 sentences in **natural, conversational Vietnamese**.
    - Be polite but not overly formal (avoid "robotic" or "template" language).
    - **DO NOT** use emojis.
    - **DO NOT** provide a long self-introduction.
    - Ensure every generated message is slightly different to avoid spam flags.
4. **Greeting**: If landlord name is known, address them by name (e.g., "Chào Trân").
   If unknown, use "Chào anh/chị".

## Listing Context
- Landlord name: {landlord_name}
- Address: {address}
- Price: {price}
- Area: {area}
- District: {district}

{custom_notes_section}

## Message Examples (for style reference ONLY - do not copy verbatim):
- "Hi, I saw the room listing in {district} for {price}. Is it still available?"
- "Hello, I'm interested in the apartment at {address}. Can I come see it this afternoon?"
- "Hi, is the {area} room in {district} still for rent? When can I schedule a viewing?"

Return ONLY the message text, with no extra explanation or markdown formatting."""

# ---------------------------------------------------------------------------
# Area Research — TinyFish goal + scoring prompt
# ---------------------------------------------------------------------------

CRITERIA_INSTRUCTIONS: dict[str, str] = {
    "food_shopping": (
        'Search "restaurants near {address}", "supermarkets near {address}", '
        '"convenience stores near {address}". Note names, types, and approximate distances.'
    ),
    "healthcare": (
        'Search "hospitals near {address}", "clinics near {address}", '
        '"pharmacies near {address}". Note names, types (public/private), and distances.'
    ),
    "education_family": (
        'Search "schools near {address}", "kindergartens near {address}", '
        '"preschools near {address}". '
        "Note names, levels (primary/secondary/international), distances."
    ),
    "transportation": (
        'Search "bus stops near {address}", "metro stations near {address}". '
        "Note public transit options and distances. Check if major roads are accessible."
    ),
    "entertainment_sports": (
        'Search "gyms near {address}", "parks near {address}", '
        '"cinemas near {address}", "cafes near {address}". Note names and distances.'
    ),
    "street_atmosphere": (
        "This criterion is assessed via Street View. No additional search needed — "
        "the Street View walk will provide observations about street width, cleanliness, "
        "building condition, greenery, and overall vibe."
    ),
    "security": (
        "Look for security features visible in the area: gated alleys, security cameras, "
        "guard booths, community watch signs. Also note lighting quality and whether the "
        "area feels residential and stable."
    ),
}

GOAL_AREA_RESEARCH = """\
## Objective

Extract neighbourhood amenity data and synthesize a Street View visual assessment \
for a specific address.

## Target

Google Maps (https://www.google.com/maps)

## Steps

1. **Navigate to Google Maps.**

2. **Enter the target address** in the main search box and press Enter.

3. **Wait for the left-hand information panel** to display the address \
and for the red pin to drop on the map.

> **IMPORTANT:** You MUST remember the exact location and visual context of this red pin, \
as you will need to return to it.

4. **Assess Amenities (Nearby Search):**
   - Click the "Nearby" button (a magnifying glass icon in the left information panel).
   - For each of the following criteria, type the query into the search box and press Enter:
     {criteria_instructions}
   - For each search, extract ONLY the top 3 relevant places from the left panel \
(Name, Type, Distance, and any notable detail).
   - Click the "X" in the search box or the "Back" arrow to return to the primary \
address pin before searching the next criterion.

5. **Enter Street View:**
   - Return to the main address view. In the left panel, click the image thumbnail \
overlaid with a circular arrow (labeled "Street View & 360°").
   - **Fallback:** If that thumbnail is missing, drag the yellow "Pegman" icon \
from the bottom right corner and drop it on the blue line nearest to the red pin.

6. **Explore and Extract Visual Data:**
   - Pan the camera 360 degrees to look at the target address, adjacent buildings, \
and the street opposite.
   - Walk 50-100m in both directions by clicking the white directional chevrons/arrows.
   - Actively memorize the infrastructure (road width, surface), environment \
(litter, greenery), structure conditions, and security features (lamps, gates, bars).
   - Infer the noise and vibe based on traffic density and zoning (commercial vs residential).

## Guardrails

- Do NOT click on external website links for any businesses. Stay inside Google Maps.
- Do NOT extract more than 3 places per amenity criterion to avoid timeouts.
- Do NOT guess. If an attribute (like security features) is not visible, state "none visible".

## Edge Cases

- If no places are found for a nearby search, return an empty array `[]` for "places".
- If Street View is completely unavailable for the address, set `street_view.description` \
to "Street View not available for this location" and set all other `street_view` fields to `null`.

## Output Format

Return ONLY a JSON object matching this exact structure and using these sample values \
as a guide for your data types. Do NOT wrap the JSON in markdown fences. \
Do NOT include any conversational text.

{{
"neighbourhood_assessment": {{
  "address": "<address>",
  "amenities": {{
    "<criterion_key>": {{
    "places": [
    {{
    "name": "Joe's Coffee Shop",
    "type": "Cafe",
    "distance": "150m",
    "notes": "Closes at 5 PM"
    }}
    ],
    "summary": "Well-served by local cafes within walking distance."
    }}
    }},
    "street_view": {{
    "description": "Tree-lined, two-lane asphalt road. Well-paved sidewalks. \
Adjacent single-family homes in good repair. No heavy traffic observed.",
    "width": "medium street",
    "condition": "good",
    "cleanliness": "very clean",
    "greenery": "abundant",
    "lighting": "adequate",
    "security_features": "none visible",
    "noise_level": "quiet",
    "building_condition": "good repair",
    "overall_vibe": "A peaceful, well-maintained residential neighbourhood."
    }}
  }}
}}

## Address

{address}"""


RESEARCH_SCORING_PROMPT = """\
You are an expert neighbourhood evaluator for the Vietnamese rental market.

Given raw observations from a Google Maps research session, score each \
criterion on a 1-10 scale and provide a brief verdict.

## Scoring Rubric (per criterion)
| Score | Meaning |
|-------|---------|
| 1-2   | Nothing available / Dangerous / Very poor |
| 3-4   | Very limited options, far away (> 2km) |
| 5-6   | Basic options available within 1km |
| 7-8   | Good variety, walkable (< 500m), reliable |
| 9-10  | Excellent — abundant, diverse, very close |

## Raw Observations
{raw_observations}

## Criteria to Score
{criteria_list}

## Instructions
1. For each criterion, assign a score (integer 1-10).
2. Provide 2-3 highlight bullet points in English.
3. Include detailed sub-findings as key-value pairs in a list format.
4. Calculate the overall score as the average of all criteria scores, \
rounded to one decimal.
5. Write a verdict (1-2 sentences in English) summarizing the \
neighbourhood's suitability for living.

## Output format
Return ONLY a JSON object matching this EXACT structure:

{{"overall": 8.2,
  "verdict": "Good choice for families, quiet alley...",
  "criteria": [
    {{
      "criterion_key": "food_shopping",
      "score": 9,
      "label": "Food & Shopping",
      "highlights": ["High density of restaurants", "Fresh food store available"],
      "details": [{{"key": "dining", "value": "..."}}, {{"key": "grocery", "value": "..."}}],
      "walking_distance": true
    }},
    {{
      "criterion_key": "healthcare",
      "score": 7,
      "label": "Healthcare",
      "highlights": ["Clinic nearby", "24/7 pharmacy"],
      "details": [{{"key": "hospital", "value": "..."}}, {{"key": "pharmacy", "value": "..."}}],
      "walking_distance": false
    }}
  ]
}}

CRITICAL:
- "criteria" MUST be an array/list of objects, NOT a dictionary/map
- Each criterion object MUST have "criterion_key" field matching the key from the criteria list
- "details" MUST be an array of {{"key": "...", "value": "..."}} objects, NOT a dictionary

Return valid JSON only. No markdown fences."""


def build_research_goal(address: str, criteria: list[str]) -> str:
    """Build a TinyFish goal string for area research."""
    instructions_parts = []
    for i, key in enumerate(criteria, 1):
        instruction = CRITERIA_INSTRUCTIONS.get(key, "")
        if instruction:
            instructions_parts.append(f"{i}. **{key}**: {instruction}")

    criteria_block = "\n".join(instructions_parts).format(address=address)

    return GOAL_AREA_RESEARCH.format(
        address=address,
        criteria_instructions=criteria_block,
    )


# ---------------------------------------------------------------------------
# Helper to pick the right goal template for a URL
# ---------------------------------------------------------------------------

_DOMAIN_TEMPLATES: dict[str, str] = {
    "facebook.com": GOAL_FACEBOOK_GROUP,
    "fb.com": GOAL_FACEBOOK_GROUP,
    "nhatot.com": GOAL_NHATOT,
    "batdongsan.com.vn": GOAL_BATDONGSAN,
}


def build_goal(url: str, query: str, user_preference: str | None = None) -> str:
    """Build a TinyFish goal string for the given URL and user query.

    Selects the appropriate template based on domain and fills in
    placeholders.
    """
    from urllib.parse import urlparse

    domain = urlparse(url).hostname or ""
    domain = domain.removeprefix("www.").removeprefix("m.")

    template = GOAL_GENERIC
    for pattern, tmpl in _DOMAIN_TEMPLATES.items():
        if pattern in domain:
            template = tmpl
            break

    preference_line = ""
    if user_preference:
        preference_line = f"User preferences: {user_preference}"

    return template.format(
        query=query,
        preference_line=preference_line,
        schema_block=LISTING_SCHEMA_SAMPLE,
    )

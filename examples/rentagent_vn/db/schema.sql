-- RentAgent VN database schema

CREATE TABLE IF NOT EXISTS campaigns (
  id TEXT PRIMARY KEY DEFAULT (hex(randomblob(6))),
  name TEXT NOT NULL DEFAULT 'Chiến dịch mới',
  preferences_json TEXT NOT NULL DEFAULT '{}',
  sources_json TEXT NOT NULL DEFAULT '[]',
  scan_frequency TEXT NOT NULL DEFAULT 'manual',
  status TEXT NOT NULL DEFAULT 'active',
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS listings (
  id TEXT PRIMARY KEY DEFAULT (hex(randomblob(6))),
  campaign_id TEXT NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
  stage TEXT NOT NULL DEFAULT 'new',
  fingerprint TEXT NOT NULL,
  title TEXT,
  description TEXT,
  price_vnd REAL,
  price_display TEXT,
  deposit_vnd REAL,
  address TEXT,
  district TEXT,
  city TEXT DEFAULT 'Ho Chi Minh',
  area_sqm REAL,
  bedrooms INTEGER,
  bathrooms INTEGER,
  listing_url TEXT,
  thumbnail_url TEXT,
  posted_date TEXT,
  source_platform TEXT,
  landlord_name TEXT,
  landlord_phone TEXT,
  landlord_zalo TEXT,
  landlord_facebook_url TEXT,
  landlord_contact_method TEXT,
  match_score REAL,
  skip_reason TEXT,
  user_notes TEXT,
  scan_id TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE(campaign_id, fingerprint)
);

CREATE TABLE IF NOT EXISTS scans (
  id TEXT PRIMARY KEY DEFAULT (hex(randomblob(6))),
  campaign_id TEXT NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
  job_id TEXT,
  status TEXT NOT NULL DEFAULT 'running',
  listings_found INTEGER DEFAULT 0,
  new_listings INTEGER DEFAULT 0,
  errors_json TEXT DEFAULT '[]',
  started_at TEXT NOT NULL DEFAULT (datetime('now')),
  completed_at TEXT
);

CREATE TABLE IF NOT EXISTS activity_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  campaign_id TEXT NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
  scan_id TEXT,
  event_type TEXT NOT NULL,
  message TEXT NOT NULL,
  metadata_json TEXT DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS outreach_messages (
  id TEXT PRIMARY KEY DEFAULT (hex(randomblob(6))),
  listing_id TEXT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
  campaign_id TEXT NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
  draft_text TEXT NOT NULL,
  final_text TEXT,
  status TEXT NOT NULL DEFAULT 'drafted',
  landlord_phone TEXT,
  zalo_user_id TEXT,
  sent_at TEXT,
  error_message TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_listings_campaign_stage ON listings(campaign_id, stage);
CREATE INDEX IF NOT EXISTS idx_listings_fingerprint ON listings(campaign_id, fingerprint);
CREATE INDEX IF NOT EXISTS idx_scans_campaign ON scans(campaign_id);
CREATE INDEX IF NOT EXISTS idx_activity_campaign ON activity_log(campaign_id);
CREATE TABLE IF NOT EXISTS area_research (
  id TEXT PRIMARY KEY DEFAULT (hex(randomblob(6))),
  listing_id TEXT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
  campaign_id TEXT NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
  status TEXT NOT NULL DEFAULT 'queued',
  criteria_json TEXT NOT NULL DEFAULT '[]',
  scores_json TEXT,
  result_json TEXT,
  verdict TEXT,
  overall_score REAL,
  street_view_urls_json TEXT DEFAULT '[]',
  auto_outreach_enabled INTEGER DEFAULT 0,
  auto_outreach_threshold REAL,
  auto_outreach_conditions_json TEXT,
  auto_outreach_triggered INTEGER DEFAULT 0,
  tinyfish_job_id TEXT,
  error_message TEXT,
  started_at TEXT,
  completed_at TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_outreach_listing ON outreach_messages(listing_id);
CREATE INDEX IF NOT EXISTS idx_outreach_campaign ON outreach_messages(campaign_id);
CREATE INDEX IF NOT EXISTS idx_area_research_listing ON area_research(listing_id);
CREATE INDEX IF NOT EXISTS idx_area_research_campaign ON area_research(campaign_id);
CREATE INDEX IF NOT EXISTS idx_area_research_status ON area_research(campaign_id, status);

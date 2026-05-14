-- SQLite: ocean + transit lookup tables (replaces CSVs under data/).
-- Apply:  sqlite3 path/to/costings.db < database/init_ocean_transit_lookups.sql
-- Safe to re-run: uses IF NOT EXISTS / INSERT OR IGNORE where appropriate.

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------------
-- Port code → city (same as former data/portcode_portcity.csv)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS portcode_portcity (
    PortCode TEXT NOT NULL PRIMARY KEY,
    PortCity TEXT NOT NULL
);

INSERT OR REPLACE INTO portcode_portcity (PortCode, PortCity) VALUES
    ('USCHS', 'Charleston'),
    ('USDAL', 'Dallas'),
    ('USHOU', 'Houston'),
    ('USMEM', 'Memphis'),
    ('USORF', 'Norfolk'),
    ('USSAV', 'Savannah'),
    ('USMSY', 'New Orleans'),
    ('USMOB', 'Mobile'),
    ('USLAX', 'Los Angeles'),
    ('USLGB', 'Long Beach');

-- ---------------------------------------------------------------------------
-- Former data/dischargeport_country.csv (unDest → label used as Destination)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dischargeport_country (
    discharge_port TEXT NOT NULL PRIMARY KEY,
    country TEXT NOT NULL
);

INSERT OR IGNORE INTO dischargeport_country (discharge_port, country) VALUES
    ('USNYC', 'United States'),
    ('USLAX', 'United States'),
    ('USHOU', 'United States'),
    ('CNSHA', 'China'),
    ('CNNGB', 'China'),
    ('VNSGN', 'Vietnam'),
    ('VNDAD', 'Vietnam'),
    ('INNSA', 'India'),
    ('KRPUS', 'South Korea'),
    ('JPYOK', 'Japan'),
    ('SGSIN', 'Singapore'),
    ('MYPKG', 'Malaysia'),
    ('THLCH', 'Thailand'),
    ('IDJKT', 'Indonesia'),
    ('PHMNL', 'Philippines'),
    ('TWKHH', 'Taiwan'),
    ('BRSSZ', 'Brazil'),
    ('MXVER', 'Mexico');

-- Add the rest of your lanes with:
--   INSERT OR IGNORE INTO dischargeport_country (discharge_port, country) VALUES ('UNLOC', 'Label');

-- ---------------------------------------------------------------------------
-- Former data/countrycode_country.csv (first 2 chars of unDest → country name)
-- Names align with server.py dthc_prepaid keys (lowercased for lookup).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS countrycode_country (
    countrycode TEXT NOT NULL PRIMARY KEY,
    country TEXT NOT NULL
);

INSERT OR IGNORE INTO countrycode_country (countrycode, country) VALUES
    ('US', 'United States'),
    ('CN', 'China'),
    ('VN', 'Vietnam'),
    ('IN', 'India'),
    ('KR', 'South Korea'),
    ('JP', 'Japan'),
    ('SG', 'Singapore'),
    ('MY', 'Malaysia'),
    ('TH', 'Thailand'),
    ('ID', 'Indonesia'),
    ('PH', 'Philippines'),
    ('TW', 'Taiwan'),
    ('HK', 'Hong Kong'),
    ('BR', 'Brazil'),
    ('MX', 'Mexico'),
    ('BD', 'Bangladesh'),
    ('PK', 'Pakistan'),
    ('LK', 'Sri Lanka'),
    ('EG', 'Egypt'),
    ('SA', 'Saudi Arabia'),
    ('AE', 'United Arab Emirates'),
    ('QA', 'Qatar'),
    ('BH', 'Bahrain'),
    ('TR', 'Turkey'),
    ('GR', 'Greece'),
    ('IT', 'Italy'),
    ('PT', 'Portugal'),
    ('ES', 'Spain'),
    ('MA', 'Morocco'),
    ('TN', 'Tunisia'),
    ('DZ', 'Algeria'),
    ('CO', 'Colombia'),
    ('EC', 'Ecuador'),
    ('PE', 'Peru'),
    ('GT', 'Guatemala'),
    ('PL', 'Poland'),
    ('DE', 'Germany'),
    ('NL', 'Netherlands'),
    ('BE', 'Belgium'),
    ('FR', 'France'),
    ('GB', 'United Kingdom');

-- ---------------------------------------------------------------------------
-- Former data/470OceanRatesExtract.csv (one row per rate lane)
-- Column names mirror DictReader keys used in server.py /api/ocean.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ocean_rates_extract (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    unOrig TEXT NOT NULL,
    unDest TEXT NOT NULL,
    ALLIN40HC REAL,
    "40FT" REAL,
    scacCode TEXT,
    expirationDate TEXT
);

CREATE INDEX IF NOT EXISTS idx_ocean_rates_extract_unOrig ON ocean_rates_extract (unOrig);
CREATE INDEX IF NOT EXISTS idx_ocean_rates_extract_unDest ON ocean_rates_extract (unDest);

-- No seed rows here (lanes are many). Bulk load from your extract, e.g. sqlite3 CLI:
--   .mode csv
--   .import --skip 1 data/470OceanRatesExtract.csv ocean_rates_extract
-- If headers differ, use a staging table or trim columns first.

-- ---------------------------------------------------------------------------
-- Former data/excel_orig/otr_transit_lookup.csv (only DEST_PORT is read)
-- Used to map OTR destinations → export port names (substring match).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS otr_transit_lookup (
    dest_port TEXT NOT NULL PRIMARY KEY
);

INSERT OR IGNORE INTO otr_transit_lookup (dest_port) VALUES
    ('Charleston'),
    ('Dallas'),
    ('Houston'),
    ('Memphis'),
    ('Norfolk'),
    ('Savannah'),
    ('New Orleans'),
    ('Mobile'),
    ('Los Angeles'),
    ('Long Beach'),
    ('Weslaco'),
    ('Shelby'),
    ('Baltimore'),
    ('Jacksonville'),
    ('Miami'),
    ('Tampa'),
    ('Oakland'),
    ('Seattle'),
    ('Chicago'),
    ('Atlanta'),
    ('Detroit'),
    ('Columbus'),
    ('Louisville'),
    ('Nashville'),
    ('Kansas City'),
    ('St. Louis'),
    ('Denver'),
    ('Phoenix'),
    ('El Paso'),
    ('San Antonio'),
    ('Corpus Christi'),
    ('Laredo'),
    ('McAllen'),
    ('Brownsville');

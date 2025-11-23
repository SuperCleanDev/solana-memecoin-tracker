"""
بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ
Configuration for Solana Memecoin Tracker
All your criteria and settings in one place
Edit these values anytime on GitHub without recoding
"""

# ============================================
# BITQUERY API CONFIGURATION
# ============================================

BITQUERY_API_URL = "https://graphql.bitquery.io"

# ============================================
# ANALYSIS WINDOW CONFIGURATION
# ============================================

ANALYSIS_WINDOW = {
    # UI window determines which tokens to track (by launch time)
    'mode': 'ui_selected',
    
    # Track each token for 24 hours from its launch
    # Even if it's outside the UI window
    'tracking_duration_hours': 12,
}

# ============================================
# SUCCESSFUL TOKEN CRITERIA
# ============================================

SUCCESSFUL_TOKEN_CONFIG = {
    # Entry window definition
    'entry_start': 'launch_time',           # Always the exact launch time
    'entry_end_mc_threshold': 20000,        # When MC hits $25K (entry window closes)
    'entry_end_fallback_minutes': 5,        # If launches above $25K: use launch + 5 mins
    
    # Success criteria (MINIMUMS - no upper limits)
    'min_roi_multiplier': 50,               # Must do at least 50x from entry_end
    'min_peak_mc': 1000000,                 # Must hit at least $1.25M (50x of $25K)
    
    # Holder snapshot timing
    'holder_snapshot_before_peak_minutes': 10,  # Snapshot 10 mins before peak
}

# ============================================
# FAILED TOKEN CRITERIA
# ============================================

FAILED_TOKEN_CONFIG = {
    # Type 1: Pump & Dump
    'pump_and_dump': {
        'enabled': True,
        'min_initial_mc': 15000,            # Must show initial promise
        'max_peak_mc': 100000,              # But never moon (< $100K)
        'min_tank_percentage': 80,          # Tanks 80%+ from peak
    },
    
    # Type 2: Rug Pull
    'rug_pull': {
        'enabled': True,
        'min_initial_mc': 15000,            # Must show initial promise
        'max_final_liquidity': 5000,        # Liquidity pulled (< $5K)
    },
    
    # Type 3: Dev Dump (PHASE 2 - Disabled for now)
    'dev_dump': {
        'enabled': False,
        'min_initial_mc': 15000,
        'dev_sold_percentage': 50,
    },
    
    # Entry window for failed tokens
    'entry_window_minutes': 30,             # First 30 mins after launch
}

# ============================================
# PROCESSING LIMITS
# ============================================

# Maximum tokens to save per category
MAX_SUCCESSFUL_TOKENS = 200
MAX_FAILED_TOKENS = 300

# Maximum tokens to process in one run (API limit protection)
MAX_TOKENS_TO_PROCESS = 500

# Batch size for progress updates
BATCH_SIZE = 50

# ============================================
# EXTERNAL APIs
# ============================================

# Solscan API for token supply verification
SOLSCAN_API_URL = "https://api.solscan.io"

# Pump.fun default supply (1 billion tokens standard)
PUMPFUN_DEFAULT_SUPPLY = 1000000000

# ============================================
# OUTPUT CONFIGURATION
# ============================================

# Output directory for JSON files
OUTPUT_DIR = "output"

# Date format for filenames and timestamps
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# ============================================
# UI CONFIGURATION
# ============================================

# Prime time presets for quick selection
TIME_RANGE_PRESETS = {
    'Prime Time (14:00-22:00 UTC)': {
        'start': '14:00:00',
        'end': '22:00:00',
        'description': 'Peak trading hours - highest success rate'
    },
    'Morning Session (06:00-14:00 UTC)': {
        'start': '06:00:00',
        'end': '14:00:00',
        'description': 'Asian/Early Europe hours'
    },
    'Full Day (00:00-23:59 UTC)': {
        'start': '00:00:00',
        'end': '23:59:59',
        'description': 'Complete 24-hour analysis'
    },
    'Custom': {
        'start': None,
        'end': None,
        'description': 'Select your own time range'
    }
}

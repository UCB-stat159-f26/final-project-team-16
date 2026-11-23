"""Settings that every script, test, and notebook of the project shares."""

# Seed for every random step, so that each run gives the same numbers.
SEED = 159

# Time zone of all local dates and times in the analysis.
LOCAL_TIME_ZONE = "America/Los_Angeles"

# Analysis window for Calls for Service, crime cases, and collisions,
# as inclusive local dates.
ANALYSIS_START = "2021-01-01"
ANALYSIS_END = "2025-12-31"

# Text format of local dates in the project, for example "2024-11-03".
DATE_FORMAT = "%Y-%m-%d"

# Call Type groups of Calls for Service. Each entry is an exact, full label
# of the Call Type column; match with equality (isin), never by substring,
# because "CFS 415 - Disturbance" and "CFS 243E1 - Domestic Violence" are
# other call types.
# Noise calls.
NOISE_CALL_TYPES = ("CFS 415E - Noise Disturbance", "CFS LDRPT - Loud Report")
# Battery and assault calls.
BATTERY_CALL_TYPES = (
    "CFS 242 - Battery",
    "CFS 243 - Serious Battery",
    "CFS 245 - Assault w/Deadly Weapon",
)
# Reckless driving calls.
RECKLESS_CALL_TYPES = ("CFS 23103 - Reckless Vehicle",)

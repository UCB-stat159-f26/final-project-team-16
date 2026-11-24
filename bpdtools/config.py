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

# Incident_Type labels of the crime cases that count as assault. Matching is
# exact: other labels such as "Domestic violence" are not included.
ASSAULT_INCIDENT_TYPES = ("Assault/Battery Misdemeanor", "Assault/Battery Felony")

# Map point of 2100 MARTIN LUTHER KING JR WAY, the Berkeley Police Department
# headquarters, as the crime cases layer writes it. The layer also gives this
# point to many cases at other addresses. For those cases it is a placeholder,
# not the place of the case.
PLACEHOLDER_LAT = 37.87022021065617
PLACEHOLDER_LON = -122.27285493558117
# Block_Address of the headquarters, in upper case with single spaces. Only a
# case at this address keeps the placeholder point as its location.
HEADQUARTERS_ADDRESS = "2100 MARTIN LUTHER KING JR WAY"

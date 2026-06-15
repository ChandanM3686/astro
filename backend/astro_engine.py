"""
Vedic Astrology Calculation Engine
===================================
Pure-Python implementation using astronomical algorithms from
Jean Meeus ("Astronomical Algorithms") and Paul Schlyter.

Computes: planet positions (sidereal), house cusps, nakshatras,
Vimshottari Dasha, KP sub-lords, yogas, daily horoscope, lucky info.
"""

import math
from datetime import datetime, timedelta
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

# ─────────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────────

RASHI_NAMES = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

RASHI_LORDS = [
    "Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
    "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter"
]

NAKSHATRA_NAMES = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha",
    "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
]

# Nakshatra lords cycle: Ketu, Venus, Sun, Moon, Mars, Rahu, Jupiter, Saturn, Mercury
NAKSHATRA_LORD_CYCLE = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
NAKSHATRA_LORDS = NAKSHATRA_LORD_CYCLE * 3  # 27 nakshatras

# Vimshottari Dasha years for each planet
DASHA_YEARS = {
    "Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7,
    "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17
}
DASHA_TOTAL = 120  # Total Vimshottari cycle = 120 years

# Planet indices for internal use
PLANET_NAMES = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]

# KP Sub-lord divisions (249 sub-divisions of the zodiac)
KP_SUB_PROPORTIONS = {p: DASHA_YEARS[p] / DASHA_TOTAL for p in NAKSHATRA_LORD_CYCLE}

# Lucky colors mapped to planets
LUCKY_COLORS = {
    "Sun": "Orange", "Moon": "White", "Mars": "Red", "Mercury": "Green",
    "Jupiter": "Yellow", "Venus": "Pink", "Saturn": "Blue",
    "Rahu": "Smoky Grey", "Ketu": "Brown"
}

# Lucky numbers mapped to planets
LUCKY_NUMBERS = {
    "Sun": [1, 10, 19], "Moon": [2, 11, 20], "Mars": [9, 18, 27],
    "Mercury": [5, 14, 23], "Jupiter": [3, 12, 21], "Venus": [6, 15, 24],
    "Saturn": [8, 17, 26], "Rahu": [4, 13, 22], "Ketu": [7, 16, 25]
}

# Day rulers
DAY_RULERS = {
    0: "Moon",    # Monday
    1: "Mars",    # Tuesday
    2: "Mercury", # Wednesday
    3: "Jupiter", # Thursday
    4: "Venus",   # Friday
    5: "Saturn",  # Saturday
    6: "Sun"      # Sunday
}

# Hora rulers (planetary hours) starting from sunrise
HORA_SEQUENCE = ["Sun", "Venus", "Mercury", "Moon", "Saturn", "Jupiter", "Mars"]


# ─────────────────────────────────────────────
#  GEOCODING
# ─────────────────────────────────────────────

_geocoder = Nominatim(user_agent="vedic_astrology_app", timeout=10)

def geocode_place(place_name: str) -> tuple:
    """Convert a place name to (latitude, longitude, timezone_offset_hours).
    Returns (lat, lon, tz_offset). Uses a rough timezone estimate from longitude.
    """
    try:
        location = _geocoder.geocode(place_name)
        if location is None:
            raise ValueError(f"Could not geocode place: {place_name}")
        lat, lon = location.latitude, location.longitude
        # Rough timezone estimate from longitude (each 15° = 1 hour)
        tz_offset = round(lon / 15.0 * 2) / 2  # Round to nearest 0.5
        return lat, lon, tz_offset
    except GeocoderTimedOut:
        raise ValueError(f"Geocoding timed out for: {place_name}")


# ─────────────────────────────────────────────
#  JULIAN DAY & TIME UTILITIES
# ─────────────────────────────────────────────

def julian_day(year: int, month: int, day: int, hour: float = 0.0) -> float:
    """Calculate Julian Day Number from calendar date/time (UT)."""
    if month <= 2:
        year -= 1
        month += 12
    A = int(year / 100)
    B = 2 - A + int(A / 4)
    jd = int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + hour / 24.0 + B - 1524.5
    return jd


def jd_to_datetime(jd: float) -> datetime:
    """Convert Julian Day back to a datetime object."""
    jd = jd + 0.5
    Z = int(jd)
    F = jd - Z
    if Z < 2299161:
        A = Z
    else:
        alpha = int((Z - 1867216.25) / 36524.25)
        A = Z + 1 + alpha - int(alpha / 4)
    B = A + 1524
    C = int((B - 122.1) / 365.25)
    D = int(365.25 * C)
    E = int((B - D) / 30.6001)
    day = B - D - int(30.6001 * E) 
    month = E - 1 if E < 14 else E - 13
    year = C - 4716 if month > 2 else C - 4715
    hour_frac = F * 24.0
    hour = int(hour_frac)
    minute = int((hour_frac - hour) * 60)
    return datetime(year, month, day, hour, minute)


def centuries_from_j2000(jd: float) -> float:
    """Julian centuries from J2000.0 epoch."""
    return (jd - 2451545.0) / 36525.0


# ─────────────────────────────────────────────
#  AYANAMSA (LAHIRI)
# ─────────────────────────────────────────────

def lahiri_ayanamsa(jd: float) -> float:
    """Calculate Lahiri Ayanamsa at the given Julian Day.
    Based on the IAU-approved Lahiri value.
    """
    T = centuries_from_j2000(jd)
    # Lahiri ayanamsa polynomial (degrees)
    ayan = 23.856 + 1.3972 * T + 0.0003086 * T * T
    return ayan


# ─────────────────────────────────────────────
#  PLANET POSITIONS (Simplified Keplerian + perturbations)
# ─────────────────────────────────────────────

def _normalize_degrees(deg: float) -> float:
    """Normalize angle to 0-360 range."""
    return deg % 360.0


def _deg_to_rad(deg: float) -> float:
    return math.radians(deg)


def _rad_to_deg(rad: float) -> float:
    return math.degrees(rad)


def _solve_kepler(M: float, e: float, tol: float = 1e-8) -> float:
    """Solve Kepler's equation M = E - e*sin(E) for E (radians)."""
    M_rad = _deg_to_rad(M)
    E = M_rad
    for _ in range(100):
        dE = (M_rad - E + e * math.sin(E)) / (1.0 - e * math.cos(E))
        E += dE
        if abs(dE) < tol:
            break
    return E


def _true_anomaly(M: float, e: float) -> float:
    """Calculate true anomaly from mean anomaly and eccentricity (degrees)."""
    E = _solve_kepler(M, e)
    v = 2.0 * math.atan2(
        math.sqrt(1 + e) * math.sin(E / 2.0),
        math.sqrt(1 - e) * math.cos(E / 2.0)
    )
    return _rad_to_deg(v)


def _sun_position(jd: float) -> float:
    """Calculate Sun's tropical ecliptic longitude (degrees).
    Uses the simplified solar position algorithm.
    """
    T = centuries_from_j2000(jd)
    # Mean longitude
    L0 = _normalize_degrees(280.46646 + 36000.76983 * T + 0.0003032 * T * T)
    # Mean anomaly
    M = _normalize_degrees(357.52911 + 35999.05029 * T - 0.0001537 * T * T)
    M_rad = _deg_to_rad(M)
    # Equation of center
    C = (1.914602 - 0.004817 * T - 0.000014 * T * T) * math.sin(M_rad) \
      + (0.019993 - 0.000101 * T) * math.sin(2 * M_rad) \
      + 0.000289 * math.sin(3 * M_rad)
    # Sun's true longitude
    sun_lon = _normalize_degrees(L0 + C)
    return sun_lon


def _moon_position(jd: float) -> float:
    """Calculate Moon's tropical ecliptic longitude (degrees).
    Simplified Meeus algorithm with major perturbation terms.
    """
    T = centuries_from_j2000(jd)

    # Moon's mean longitude
    Lp = _normalize_degrees(218.3164477 + 481267.88123421 * T
                            - 0.0015786 * T**2 + T**3 / 538841.0 - T**4 / 65194000.0)
    # Mean elongation
    D = _normalize_degrees(297.8501921 + 445267.1114034 * T
                           - 0.0018819 * T**2 + T**3 / 545868.0 - T**4 / 113065000.0)
    # Sun's mean anomaly
    M = _normalize_degrees(357.5291092 + 35999.0502909 * T
                           - 0.0001536 * T**2 + T**3 / 24490000.0)
    # Moon's mean anomaly
    Mp = _normalize_degrees(134.9633964 + 477198.8675055 * T
                            + 0.0087414 * T**2 + T**3 / 69699.0 - T**4 / 14712000.0)
    # Moon's argument of latitude
    F = _normalize_degrees(93.2720950 + 483202.0175233 * T
                           - 0.0036539 * T**2 - T**3 / 3526000.0 + T**4 / 863310000.0)

    D_r, M_r, Mp_r, F_r = [_deg_to_rad(x) for x in [D, M, Mp, F]]

    # Major longitude perturbation terms (in degrees)
    lon_terms = (
        6.288774 * math.sin(Mp_r)
        + 1.274027 * math.sin(2 * D_r - Mp_r)
        + 0.658314 * math.sin(2 * D_r)
        + 0.213618 * math.sin(2 * Mp_r)
        - 0.185116 * math.sin(M_r)
        - 0.114332 * math.sin(2 * F_r)
        + 0.058793 * math.sin(2 * D_r - 2 * Mp_r)
        + 0.057066 * math.sin(2 * D_r - M_r - Mp_r)
        + 0.053322 * math.sin(2 * D_r + Mp_r)
        + 0.045758 * math.sin(2 * D_r - M_r)
        - 0.040923 * math.sin(M_r - Mp_r)
        - 0.034720 * math.sin(D_r)
        - 0.030383 * math.sin(M_r + Mp_r)
        + 0.015327 * math.sin(2 * D_r - 2 * F_r)
        - 0.012528 * math.sin(Mp_r + 2 * F_r)
        + 0.010980 * math.sin(Mp_r - 2 * F_r)
    )

    moon_lon = _normalize_degrees(Lp + lon_terms)
    return moon_lon


def _mars_position(jd: float) -> float:
    """Mars tropical longitude using simplified orbital elements."""
    T = centuries_from_j2000(jd)
    # Orbital elements at epoch
    L = _normalize_degrees(355.45332 + 19140.30268 * T)
    M = _normalize_degrees(319.51913 + 19139.85475 * T)
    e = 0.09340 + 0.000090484 * T
    v = _true_anomaly(M, e)
    lon = _normalize_degrees(L + v - M)
    # Apply perturbations from Jupiter
    Mj = _normalize_degrees(20.9395 + 3034.6874 * T)
    lon += (-0.01133 * math.sin(_deg_to_rad(2 * Mj - 5 * M + 68.555))
            - 0.00933 * math.sin(_deg_to_rad(Mj - 2 * M + 68.555)))
    return _normalize_degrees(lon)


def _mercury_position(jd: float) -> float:
    """Mercury tropical longitude."""
    T = centuries_from_j2000(jd)
    L = _normalize_degrees(252.25084 + 149472.67411 * T)
    M = _normalize_degrees(174.79520 + 149472.51529 * T)
    e = 0.20563 - 0.00001961 * T
    v = _true_anomaly(M, e)
    return _normalize_degrees(L + v - M)


def _jupiter_position(jd: float) -> float:
    """Jupiter tropical longitude."""
    T = centuries_from_j2000(jd)
    L = _normalize_degrees(34.35152 + 3034.90567 * T)
    M = _normalize_degrees(20.02032 + 3034.68683 * T)
    e = 0.04849 - 0.00013253 * T
    v = _true_anomaly(M, e)
    # Saturn perturbation
    Ms = _normalize_degrees(316.96706 + 1222.49362 * T)
    pert = (0.3314 * math.sin(_deg_to_rad(2 * M - 5 * Ms - 76.0))
            + 0.1039 * math.sin(_deg_to_rad(2 * M - 5 * Ms - 153.0)))
    return _normalize_degrees(L + v - M + pert)


def _venus_position(jd: float) -> float:
    """Venus tropical longitude."""
    T = centuries_from_j2000(jd)
    L = _normalize_degrees(181.97973 + 58517.81539 * T)
    M = _normalize_degrees(50.41663 + 58517.80387 * T)
    e = 0.00677 - 0.00004778 * T
    v = _true_anomaly(M, e)
    return _normalize_degrees(L + v - M)


def _saturn_position(jd: float) -> float:
    """Saturn tropical longitude."""
    T = centuries_from_j2000(jd)
    L = _normalize_degrees(50.07747 + 1222.11379 * T)
    M = _normalize_degrees(316.96706 + 1222.49362 * T)
    e = 0.05551 - 0.00034664 * T
    v = _true_anomaly(M, e)
    # Jupiter perturbation
    Mj = _normalize_degrees(20.02032 + 3034.68683 * T)
    pert = (-0.8142 * math.sin(_deg_to_rad(2 * Mj - 5 * M - 76.0))
            + 0.1890 * math.sin(_deg_to_rad(2 * Mj - 5 * M - 153.0)))
    return _normalize_degrees(L + v - M + pert)


def _rahu_position(jd: float) -> float:
    """Mean Rahu (North Node) tropical longitude. Rahu moves retrograde."""
    T = centuries_from_j2000(jd)
    omega = _normalize_degrees(125.04452 - 1934.13626 * T + 0.00220708 * T * T)
    return omega


def _ketu_position(rahu_lon: float) -> float:
    """Ketu is always exactly opposite Rahu."""
    return _normalize_degrees(rahu_lon + 180.0)


# Planet calculation dispatch
_PLANET_FUNCTIONS = {
    "Sun": _sun_position,
    "Moon": _moon_position,
    "Mars": _mars_position,
    "Mercury": _mercury_position,
    "Jupiter": _jupiter_position,
    "Venus": _venus_position,
    "Saturn": _saturn_position,
    "Rahu": _rahu_position,
}


def get_planet_positions(jd: float) -> dict:
    """Get sidereal (Lahiri) positions for all 9 Vedic planets.
    Returns dict: {planet_name: {"longitude": deg, "rashi": name, "rashi_lord": lord,
                                  "degree_in_rashi": deg, "nakshatra": name,
                                  "nakshatra_lord": lord, "nakshatra_pada": int,
                                  "is_retrograde": bool}}
    """
    ayanamsa = lahiri_ayanamsa(jd)
    positions = {}

    for planet in PLANET_NAMES:
        if planet == "Ketu":
            continue  # Calculated from Rahu

        tropical_lon = _PLANET_FUNCTIONS[planet](jd)
        sidereal_lon = _normalize_degrees(tropical_lon - ayanamsa)

        positions[planet] = _build_planet_info(planet, sidereal_lon, jd)

    # Ketu from Rahu
    rahu_sid = positions["Rahu"]["longitude"]
    ketu_sid = _normalize_degrees(rahu_sid + 180.0)
    positions["Ketu"] = _build_planet_info("Ketu", ketu_sid, jd)

    # Simple retrograde check (compare with position 1 day earlier)
    jd_prev = jd - 1.0
    ayan_prev = lahiri_ayanamsa(jd_prev)
    for planet in PLANET_NAMES:
        if planet in ("Rahu", "Ketu"):
            positions[planet]["is_retrograde"] = True  # Nodes always retrograde
            continue
        if planet == "Sun" or planet == "Moon":
            positions[planet]["is_retrograde"] = False  # Sun/Moon never retrograde
            continue
        prev_tropical = _PLANET_FUNCTIONS[planet](jd_prev)
        prev_sidereal = _normalize_degrees(prev_tropical - ayan_prev)
        current = positions[planet]["longitude"]
        diff = current - prev_sidereal
        if diff > 180:
            diff -= 360
        elif diff < -180:
            diff += 360
        positions[planet]["is_retrograde"] = diff < 0

    return positions


def _build_planet_info(planet: str, sidereal_lon: float, jd: float) -> dict:
    """Build detailed info dict for a planet at a given sidereal longitude."""
    rashi_idx = int(sidereal_lon / 30.0)
    degree_in_rashi = sidereal_lon % 30.0

    nak_idx = int(sidereal_lon / (360.0 / 27.0))
    nak_degree = sidereal_lon % (360.0 / 27.0)
    pada = int(nak_degree / (360.0 / 108.0)) + 1  # Each nakshatra has 4 padas
    if pada > 4:
        pada = 4

    return {
        "longitude": round(sidereal_lon, 4),
        "rashi": RASHI_NAMES[rashi_idx % 12],
        "rashi_index": rashi_idx % 12,
        "rashi_lord": RASHI_LORDS[rashi_idx % 12],
        "degree_in_rashi": round(degree_in_rashi, 2),
        "nakshatra": NAKSHATRA_NAMES[nak_idx % 27],
        "nakshatra_index": nak_idx % 27,
        "nakshatra_lord": NAKSHATRA_LORDS[nak_idx % 27],
        "nakshatra_pada": pada,
        "is_retrograde": False  # Set later
    }


# ─────────────────────────────────────────────
#  HOUSE CUSPS (Placidus approximation)
# ─────────────────────────────────────────────

def _obliquity(jd: float) -> float:
    """Mean obliquity of the ecliptic (degrees)."""
    T = centuries_from_j2000(jd)
    return 23.4392911 - 0.0130042 * T - 1.64e-7 * T * T + 5.04e-7 * T * T * T


def _local_sidereal_time(jd: float, lon: float) -> float:
    """Greenwich Mean Sidereal Time + longitude offset (degrees)."""
    T = centuries_from_j2000(jd)
    gmst = 280.46061837 + 360.98564736629 * (jd - 2451545.0) + 0.000387933 * T * T
    lst = _normalize_degrees(gmst + lon)
    return lst


def get_house_cusps(jd: float, lat: float, lon: float) -> dict:
    """Calculate house cusps using Equal House system from Ascendant.
    Also returns Ascendant and MC.
    Returns dict with cusps (1-12), ascendant, mc.
    """
    ayanamsa = lahiri_ayanamsa(jd)
    lst = _local_sidereal_time(jd, lon)
    eps = _obliquity(jd)

    lst_rad = _deg_to_rad(lst)
    eps_rad = _deg_to_rad(eps)
    lat_rad = _deg_to_rad(lat)

    # Ascendant calculation
    y = -math.cos(lst_rad)
    x = math.sin(eps_rad) * math.tan(lat_rad) + math.cos(eps_rad) * math.sin(lst_rad)
    asc_tropical = _rad_to_deg(math.atan2(y, x))
    asc_tropical = _normalize_degrees(asc_tropical)
    asc_sidereal = _normalize_degrees(asc_tropical - ayanamsa)

    # MC (Midheaven) calculation
    mc_tropical = _rad_to_deg(math.atan2(math.sin(lst_rad), math.cos(lst_rad) * math.cos(eps_rad)))
    mc_tropical = _normalize_degrees(mc_tropical)
    mc_sidereal = _normalize_degrees(mc_tropical - ayanamsa)

    # Equal house system: each house = 30° from Ascendant
    cusps = {}
    for i in range(12):
        cusps[i + 1] = {
            "longitude": round(_normalize_degrees(asc_sidereal + i * 30.0), 4),
            "rashi": RASHI_NAMES[int(_normalize_degrees(asc_sidereal + i * 30.0) / 30.0) % 12],
            "degree": round(_normalize_degrees(asc_sidereal + i * 30.0) % 30.0, 2)
        }

    return {
        "cusps": cusps,
        "ascendant": round(asc_sidereal, 4),
        "ascendant_rashi": RASHI_NAMES[int(asc_sidereal / 30.0) % 12],
        "mc": round(mc_sidereal, 4),
        "mc_rashi": RASHI_NAMES[int(mc_sidereal / 30.0) % 12]
    }


# ─────────────────────────────────────────────
#  LAGNA (D1) CHART
# ─────────────────────────────────────────────

def build_lagna_chart(planets: dict, houses: dict) -> dict:
    """Build Lagna (Rashi/D1) chart showing which planets are in which house."""
    asc_lon = houses["ascendant"]
    chart = {i: [] for i in range(1, 13)}

    for planet, info in planets.items():
        # Calculate which house the planet falls in
        diff = _normalize_degrees(info["longitude"] - asc_lon)
        house_num = int(diff / 30.0) + 1
        if house_num > 12:
            house_num = 12
        chart[house_num].append({
            "planet": planet,
            "degree": info["degree_in_rashi"],
            "rashi": info["rashi"],
            "nakshatra": info["nakshatra"],
            "retrograde": info["is_retrograde"]
        })

    return chart


# ─────────────────────────────────────────────
#  NAVAMSA (D9) CHART
# ─────────────────────────────────────────────

def build_navamsa_chart(planets: dict) -> dict:
    """Build Navamsa (D9) chart. Each rashi is divided into 9 parts of 3°20'."""
    navamsa = {}
    for planet, info in planets.items():
        lon = info["longitude"]
        # Navamsa division: each 3.333... degrees = one navamsa
        navamsa_num = int(lon / (30.0 / 9.0))  # 0-107
        navamsa_rashi_idx = navamsa_num % 12
        navamsa[planet] = {
            "rashi": RASHI_NAMES[navamsa_rashi_idx],
            "rashi_lord": RASHI_LORDS[navamsa_rashi_idx],
            "navamsa_number": (navamsa_num % 9) + 1
        }
    return navamsa


# ─────────────────────────────────────────────
#  KP (KRISHNAMURTI PADDHATI) CHART
# ─────────────────────────────────────────────

def _get_kp_sublord(longitude: float) -> dict:
    """Get the Star Lord and Sub Lord for a given sidereal longitude using KP system."""
    nak_span = 360.0 / 27.0  # 13.333... degrees per nakshatra

    nak_idx = int(longitude / nak_span) % 27
    star_lord = NAKSHATRA_LORDS[nak_idx]

    # Position within nakshatra
    pos_in_nak = longitude % nak_span

    # Sub-lord: divide each nakshatra proportionally by dasha years
    cumulative = 0.0
    sub_lord = star_lord
    sub_sub_lord = star_lord

    # Find sub-lord
    lord_idx = NAKSHATRA_LORD_CYCLE.index(star_lord)
    for i in range(9):
        p = NAKSHATRA_LORD_CYCLE[(lord_idx + i) % 9]
        span = (DASHA_YEARS[p] / DASHA_TOTAL) * nak_span
        if cumulative + span > pos_in_nak:
            sub_lord = p
            # Find sub-sub-lord within this sub division
            pos_in_sub = pos_in_nak - cumulative
            sub_cumulative = 0.0
            sub_lord_idx = NAKSHATRA_LORD_CYCLE.index(sub_lord)
            for j in range(9):
                pp = NAKSHATRA_LORD_CYCLE[(sub_lord_idx + j) % 9]
                sub_span = (DASHA_YEARS[pp] / DASHA_TOTAL) * span
                if sub_cumulative + sub_span > pos_in_sub:
                    sub_sub_lord = pp
                    break
                sub_cumulative += sub_span
            break
        cumulative += span

    return {
        "star_lord": star_lord,
        "sub_lord": sub_lord,
        "sub_sub_lord": sub_sub_lord
    }


def build_kp_chart(planets: dict, houses: dict) -> dict:
    """Build KP chart with star lord, sub lord, and sub-sub lord for planets and cusps."""
    kp_planets = {}
    for planet, info in planets.items():
        kp_info = _get_kp_sublord(info["longitude"])
        kp_planets[planet] = {
            "longitude": info["longitude"],
            "rashi": info["rashi"],
            "nakshatra": info["nakshatra"],
            **kp_info
        }

    kp_cusps = {}
    for cusp_num, cusp_info in houses["cusps"].items():
        kp_info = _get_kp_sublord(cusp_info["longitude"])
        kp_cusps[f"Cusp_{cusp_num}"] = {
            "longitude": cusp_info["longitude"],
            "rashi": cusp_info["rashi"],
            **kp_info
        }

    return {"planets": kp_planets, "cusps": kp_cusps}


# ─────────────────────────────────────────────
#  VIMSHOTTARI DASHA
# ─────────────────────────────────────────────

def compute_vimshottari_dasha(moon_longitude: float, birth_jd: float) -> list:
    """Compute full Vimshottari Mahadasha-Antardasha-Pratyantardasha periods.
    Returns list of Mahadasha periods with nested Antardasha.
    """
    nak_span = 360.0 / 27.0
    nak_idx = int(moon_longitude / nak_span) % 27
    nak_lord = NAKSHATRA_LORDS[nak_idx]

    # Balance of first dasha: fraction of nakshatra remaining
    pos_in_nak = moon_longitude % nak_span
    remaining_fraction = 1.0 - (pos_in_nak / nak_span)

    # Build sequence starting from birth nakshatra lord
    lord_start_idx = NAKSHATRA_LORD_CYCLE.index(nak_lord)
    dasha_sequence = [NAKSHATRA_LORD_CYCLE[(lord_start_idx + i) % 9] for i in range(9)]

    dashas = []
    current_jd = birth_jd

    for i, lord in enumerate(dasha_sequence):
        total_years = DASHA_YEARS[lord]
        if i == 0:
            years = total_years * remaining_fraction
        else:
            years = total_years

        days = years * 365.25
        start_dt = jd_to_datetime(current_jd)
        end_jd = current_jd + days
        end_dt = jd_to_datetime(end_jd)

        # Compute Antardashas within this Mahadasha
        antardashas = []
        ad_jd = current_jd
        for j in range(9):
            ad_lord = NAKSHATRA_LORD_CYCLE[(NAKSHATRA_LORD_CYCLE.index(lord) + j) % 9]
            ad_years = years * DASHA_YEARS[ad_lord] / DASHA_TOTAL
            ad_days = ad_years * 365.25
            ad_start = jd_to_datetime(ad_jd)
            ad_end = jd_to_datetime(ad_jd + ad_days)

            antardashas.append({
                "lord": ad_lord,
                "start": ad_start.strftime("%Y-%m-%d"),
                "end": ad_end.strftime("%Y-%m-%d"),
                "years": round(ad_years, 2)
            })
            ad_jd += ad_days

        dashas.append({
            "lord": lord,
            "start": start_dt.strftime("%Y-%m-%d"),
            "end": end_dt.strftime("%Y-%m-%d"),
            "total_years": round(years, 2),
            "antardashas": antardashas
        })
        current_jd = end_jd

    return dashas


def get_current_dasha(dashas: list, current_jd: float) -> dict:
    """Find the currently running Mahadasha and Antardasha."""
    current_dt = jd_to_datetime(current_jd)
    current_str = current_dt.strftime("%Y-%m-%d")

    for md in dashas:
        if md["start"] <= current_str <= md["end"]:
            for ad in md["antardashas"]:
                if ad["start"] <= current_str <= ad["end"]:
                    return {
                        "mahadasha": md["lord"],
                        "mahadasha_start": md["start"],
                        "mahadasha_end": md["end"],
                        "antardasha": ad["lord"],
                        "antardasha_start": ad["start"],
                        "antardasha_end": ad["end"]
                    }
            return {
                "mahadasha": md["lord"],
                "mahadasha_start": md["start"],
                "mahadasha_end": md["end"],
                "antardasha": "Unknown",
                "antardasha_start": "",
                "antardasha_end": ""
            }
    return {"mahadasha": "Unknown", "antardasha": "Unknown"}


# ─────────────────────────────────────────────
#  PLANETARY ASPECTS
# ─────────────────────────────────────────────

def compute_aspects(planets: dict) -> list:
    """Compute Vedic aspects between planets.
    Vedic aspects: All planets aspect 7th from them.
    Mars also aspects 4th and 8th.
    Jupiter also aspects 5th and 9th.
    Saturn also aspects 3rd and 10th.
    """
    aspect_rules = {
        "Sun": [7], "Moon": [7], "Mercury": [7], "Venus": [7],
        "Mars": [4, 7, 8], "Jupiter": [5, 7, 9], "Saturn": [3, 7, 10],
        "Rahu": [5, 7, 9], "Ketu": [5, 7, 9]
    }

    aspects = []
    planet_list = list(planets.keys())

    for planet in planet_list:
        p_rashi_idx = planets[planet]["rashi_index"]
        aspect_houses = aspect_rules.get(planet, [7])

        for other in planet_list:
            if other == planet:
                continue
            o_rashi_idx = planets[other]["rashi_index"]
            house_diff = ((o_rashi_idx - p_rashi_idx) % 12) + 1

            if house_diff in aspect_houses:
                aspects.append({
                    "from": planet,
                    "to": other,
                    "aspect_type": f"{house_diff}th aspect",
                    "nature": _aspect_nature(planet, other)
                })

    return aspects


def _aspect_nature(planet1: str, planet2: str) -> str:
    """Determine if an aspect is benefic or malefic."""
    benefics = {"Jupiter", "Venus", "Moon", "Mercury"}
    malefics = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}

    if planet1 in benefics and planet2 in benefics:
        return "benefic"
    elif planet1 in malefics and planet2 in malefics:
        return "malefic"
    else:
        return "mixed"


# ─────────────────────────────────────────────
#  YOGA DETECTION
# ─────────────────────────────────────────────

def detect_yogas(planets: dict, houses: dict) -> list:
    """Detect major Vedic yogas based on planet positions and houses."""
    yogas = []
    asc_lon = houses["ascendant"]

    def _house_of(planet_name: str) -> int:
        diff = _normalize_degrees(planets[planet_name]["longitude"] - asc_lon)
        return int(diff / 30.0) + 1

    moon_house = _house_of("Moon")
    jupiter_house = _house_of("Jupiter")
    sun_house = _house_of("Sun")
    mercury_house = _house_of("Mercury")
    venus_house = _house_of("Venus")
    mars_house = _house_of("Mars")
    saturn_house = _house_of("Saturn")

    # 1. Gajakesari Yoga: Jupiter in kendra (1,4,7,10) from Moon
    jup_from_moon = ((jupiter_house - moon_house) % 12) + 1
    if jup_from_moon in [1, 4, 7, 10]:
        yogas.append({
            "name": "Gajakesari Yoga",
            "description": "Jupiter in kendra from Moon. Grants wisdom, wealth, fame and lasting reputation.",
            "strength": "strong" if not planets["Jupiter"]["is_retrograde"] else "moderate"
        })

    # 2. Budhaditya Yoga: Sun and Mercury in same house
    if sun_house == mercury_house:
        yogas.append({
            "name": "Budhaditya Yoga",
            "description": "Sun-Mercury conjunction. Grants sharp intellect, communication skills, and success in education.",
            "strength": "strong"
        })

    # 3. Panch Mahapurusha Yogas
    # Ruchaka Yoga: Mars in own sign or exalted, in kendra
    mars_rashi = planets["Mars"]["rashi"]
    if mars_rashi in ["Aries", "Scorpio", "Capricorn"] and mars_house in [1, 4, 7, 10]:
        yogas.append({
            "name": "Ruchaka Yoga (Panch Mahapurusha)",
            "description": "Mars in own/exalted sign in kendra. Grants courage, leadership, military success.",
            "strength": "strong"
        })

    # Bhadra Yoga: Mercury in own sign or exalted, in kendra
    merc_rashi = planets["Mercury"]["rashi"]
    if merc_rashi in ["Gemini", "Virgo"] and mercury_house in [1, 4, 7, 10]:
        yogas.append({
            "name": "Bhadra Yoga (Panch Mahapurusha)",
            "description": "Mercury in own/exalted sign in kendra. Grants eloquence, business acumen, scholarly success.",
            "strength": "strong"
        })

    # Hamsa Yoga: Jupiter in own sign or exalted, in kendra
    jup_rashi = planets["Jupiter"]["rashi"]
    if jup_rashi in ["Sagittarius", "Pisces", "Cancer"] and jupiter_house in [1, 4, 7, 10]:
        yogas.append({
            "name": "Hamsa Yoga (Panch Mahapurusha)",
            "description": "Jupiter in own/exalted sign in kendra. Grants spiritual wisdom, respect, and prosperity.",
            "strength": "strong"
        })

    # Malavya Yoga: Venus in own sign or exalted, in kendra
    ven_rashi = planets["Venus"]["rashi"]
    if ven_rashi in ["Taurus", "Libra", "Pisces"] and venus_house in [1, 4, 7, 10]:
        yogas.append({
            "name": "Malavya Yoga (Panch Mahapurusha)",
            "description": "Venus in own/exalted sign in kendra. Grants luxury, beauty, artistic talents, and a comfortable life.",
            "strength": "strong"
        })

    # Sasa Yoga: Saturn in own sign or exalted, in kendra
    sat_rashi = planets["Saturn"]["rashi"]
    if sat_rashi in ["Capricorn", "Aquarius", "Libra"] and saturn_house in [1, 4, 7, 10]:
        yogas.append({
            "name": "Sasa Yoga (Panch Mahapurusha)",
            "description": "Saturn in own/exalted sign in kendra. Grants authority, discipline, and political power.",
            "strength": "strong"
        })

    # 4. Chandra-Mangal Yoga: Moon-Mars conjunction
    if moon_house == mars_house:
        yogas.append({
            "name": "Chandra-Mangal Yoga",
            "description": "Moon-Mars conjunction. Grants wealth through entrepreneurship but can cause emotional intensity.",
            "strength": "moderate"
        })

    # 5. Dhana Yoga: Lord of 2nd/11th in kendra or trikona
    # Simplified check
    asc_rashi_idx = int(asc_lon / 30.0) % 12
    lord_2 = RASHI_LORDS[(asc_rashi_idx + 1) % 12]
    lord_11 = RASHI_LORDS[(asc_rashi_idx + 10) % 12]
    if lord_2 in planets:
        h = _house_of(lord_2)
        if h in [1, 4, 5, 7, 9, 10]:
            yogas.append({
                "name": "Dhana Yoga",
                "description": f"Lord of 2nd house ({lord_2}) in favorable position. Indicates wealth accumulation.",
                "strength": "moderate"
            })

    # 6. Raj Yoga: Lord of kendra + lord of trikona in conjunction or mutual aspect
    kendra_lords = [RASHI_LORDS[(asc_rashi_idx + h) % 12] for h in [0, 3, 6, 9]]
    trikona_lords = [RASHI_LORDS[(asc_rashi_idx + h) % 12] for h in [0, 4, 8]]
    for kl in kendra_lords:
        for tl in trikona_lords:
            if kl != tl and kl in planets and tl in planets:
                if _house_of(kl) == _house_of(tl):
                    yogas.append({
                        "name": "Raj Yoga",
                        "description": f"Kendra lord ({kl}) conjunct Trikona lord ({tl}). Indicates power, status, and authority.",
                        "strength": "strong"
                    })
                    break
        else:
            continue
        break

    # 7. Kemadruma Yoga: No planets on either side of Moon (2nd and 12th from Moon)
    house_before_moon = ((moon_house - 2) % 12) + 1
    house_after_moon = (moon_house % 12) + 1
    planets_near_moon = False
    for p in ["Mars", "Mercury", "Jupiter", "Venus", "Saturn"]:
        h = _house_of(p)
        if h == house_before_moon or h == house_after_moon:
            planets_near_moon = True
            break
    if not planets_near_moon:
        yogas.append({
            "name": "Kemadruma Yoga",
            "description": "No planets in 2nd/12th from Moon. Can indicate financial struggles, but gets cancelled by aspects.",
            "strength": "moderate"
        })

    # 8. Viparita Raj Yoga: Lords of 6th, 8th, 12th in each other's houses
    lord_6 = RASHI_LORDS[(asc_rashi_idx + 5) % 12]
    lord_8 = RASHI_LORDS[(asc_rashi_idx + 7) % 12]
    lord_12 = RASHI_LORDS[(asc_rashi_idx + 11) % 12]
    dusthana_lords = {lord_6, lord_8, lord_12}
    for dl in dusthana_lords:
        if dl in planets:
            h = _house_of(dl)
            if h in [6, 8, 12]:
                yogas.append({
                    "name": "Viparita Raj Yoga",
                    "description": f"Dusthana lord ({dl}) in dusthana house. Turns adversity into unexpected success.",
                    "strength": "moderate"
                })
                break

    return yogas


# ─────────────────────────────────────────────
#  DAILY HOROSCOPE & LUCKY PREDICTIONS
# ─────────────────────────────────────────────

def get_daily_predictions(moon_rashi: str, moon_nakshatra_lord: str, current_dt: datetime = None) -> dict:
    """Generate daily horoscope data, lucky number, color, day, time."""
    if current_dt is None:
        current_dt = datetime.utcnow()

    day_of_week = current_dt.weekday()
    day_ruler = DAY_RULERS[day_of_week]
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    # Lucky color based on Moon nakshatra lord
    lucky_color = LUCKY_COLORS.get(moon_nakshatra_lord, "White")

    # Lucky number based on Moon nakshatra lord
    lucky_nums = LUCKY_NUMBERS.get(moon_nakshatra_lord, [7])
    lucky_number = lucky_nums[current_dt.day % len(lucky_nums)]

    # Lucky day: day ruled by Moon nakshatra lord
    lucky_day_idx = [k for k, v in DAY_RULERS.items() if v == moon_nakshatra_lord]
    lucky_day = day_names[lucky_day_idx[0]] if lucky_day_idx else day_names[day_of_week]

    # Lucky time: hora of the nakshatra lord (simplified)
    hora_start = 6 + NAKSHATRA_LORD_CYCLE.index(moon_nakshatra_lord) * 2
    if hora_start > 18:
        hora_start -= 12
    lucky_time = f"{hora_start:02d}:00 - {hora_start + 2:02d}:00"

    # Moon sign based general prediction themes
    sign_themes = {
        "Aries": {"focus": "New initiatives and leadership", "avoid": "Impulsive decisions", "energy": "High"},
        "Taurus": {"focus": "Financial planning and stability", "avoid": "Stubbornness", "energy": "Steady"},
        "Gemini": {"focus": "Communication and networking", "avoid": "Overthinking", "energy": "Variable"},
        "Cancer": {"focus": "Home, family, and emotional bonds", "avoid": "Mood swings", "energy": "Nurturing"},
        "Leo": {"focus": "Creative expression and confidence", "avoid": "Ego clashes", "energy": "Vibrant"},
        "Virgo": {"focus": "Health, routine optimization", "avoid": "Over-criticism", "energy": "Analytical"},
        "Libra": {"focus": "Relationships and partnerships", "avoid": "Indecision", "energy": "Harmonious"},
        "Scorpio": {"focus": "Deep transformation, research", "avoid": "Jealousy and control", "energy": "Intense"},
        "Sagittarius": {"focus": "Learning, travel, philosophy", "avoid": "Overcommitting", "energy": "Adventurous"},
        "Capricorn": {"focus": "Career goals and discipline", "avoid": "Pessimism", "energy": "Determined"},
        "Aquarius": {"focus": "Innovation and social causes", "avoid": "Emotional detachment", "energy": "Progressive"},
        "Pisces": {"focus": "Spirituality and intuition", "avoid": "Escapism", "energy": "Dreamy"}
    }

    theme = sign_themes.get(moon_rashi, sign_themes["Aries"])

    return {
        "moon_sign": moon_rashi,
        "day_ruler": day_ruler,
        "today": current_dt.strftime("%A, %B %d, %Y"),
        "lucky_number": lucky_number,
        "lucky_color": lucky_color,
        "lucky_day": lucky_day,
        "lucky_time": lucky_time,
        "daily_theme": theme["focus"],
        "avoid_today": theme["avoid"],
        "energy_level": theme["energy"],
        "compatibility_sign": RASHI_NAMES[(RASHI_NAMES.index(moon_rashi) + 4) % 12]  # Trine sign
    }


# ─────────────────────────────────────────────
#  MAIN: COMPUTE FULL CHART
# ─────────────────────────────────────────────

def compute_full_chart(name: str, birth_date: str, birth_time: str,
                       place_of_birth: str, gender: str) -> dict:
    """Master function: compute the complete Vedic chart from user input.

    Args:
        name: User's name
        birth_date: Date string in "YYYY-MM-DD" format
        birth_time: Time string in "HH:MM" format (24-hour, local time)
        place_of_birth: City/place name
        gender: "male" or "female"

    Returns:
        Complete chart data dict with all calculations.
    """
    # 1. Parse inputs
    dt = datetime.strptime(birth_date, "%Y-%m-%d")
    hour, minute = map(int, birth_time.split(":"))
    local_hour = hour + minute / 60.0

    # 2. Geocode place
    lat, lon, tz_offset = geocode_place(place_of_birth)

    # 3. Convert local time to UT
    ut_hour = local_hour - tz_offset

    # 4. Compute Julian Day
    jd = julian_day(dt.year, dt.month, dt.day, ut_hour)

    # 5. Planet positions
    planets = get_planet_positions(jd)

    # 6. House cusps
    houses = get_house_cusps(jd, lat, lon)

    # 7. Lagna chart (D1)
    lagna_chart = build_lagna_chart(planets, houses)

    # 8. Navamsa chart (D9)
    navamsa_chart = build_navamsa_chart(planets)

    # 9. KP chart
    kp_chart = build_kp_chart(planets, houses)

    # 10. Vimshottari Dasha
    moon_lon = planets["Moon"]["longitude"]
    dashas = compute_vimshottari_dasha(moon_lon, jd)

    # 11. Current dasha
    current_jd = julian_day(
        datetime.utcnow().year, datetime.utcnow().month,
        datetime.utcnow().day, datetime.utcnow().hour + datetime.utcnow().minute / 60.0
    )
    current_dasha = get_current_dasha(dashas, current_jd)

    # 12. Aspects
    aspects = compute_aspects(planets)

    # 13. Yogas
    yogas = detect_yogas(planets, houses)

    # 14. Daily predictions
    moon_rashi = planets["Moon"]["rashi"]
    moon_nak_lord = planets["Moon"]["nakshatra_lord"]
    daily = get_daily_predictions(moon_rashi, moon_nak_lord)

    return {
        "user": {
            "name": name,
            "birth_date": birth_date,
            "birth_time": birth_time,
            "place_of_birth": place_of_birth,
            "coordinates": {"latitude": lat, "longitude": lon, "timezone": tz_offset},
            "gender": gender
        },
        "planets": planets,
        "houses": houses,
        "lagna_chart": lagna_chart,
        "navamsa_chart": navamsa_chart,
        "kp_chart": kp_chart,
        "dasha": {
            "vimshottari": dashas,
            "current": current_dasha
        },
        "aspects": aspects,
        "yogas": yogas,
        "daily": daily,
        "meta": {
            "ayanamsa": "Lahiri",
            "house_system": "Equal House",
            "julian_day": jd,
            "calculation_method": "Pure Python Astronomical Algorithms"
        }
    }

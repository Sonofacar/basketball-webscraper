# scraper/identity.py
#
# Copyright (C) 2025 Carson Buttars
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

"""Cross-source identity knowledge: normalizers and the franchise crosswalk.

The same real world entity reaches the database once per source with
different keys -- a team is ``/teams/SAS/2025.html`` on basketball-reference,
``/team/1610612759/2025`` on nba.com and ``/espn/team/10/2025`` on ESPN, and
its Abbreviation column reads ``SAS``, ``SAS`` and ``SA`` respectively. This
module is the pure-data half of Phase 2: how to canonicalize names, dates and
locations, and which source spellings belong to one franchise. It has no
database or network access; ``verify.py`` owns the matching itself.

The franchise crosswalk is a code constant rather than a database table on
purpose: aliasing is verifier knowledge, not scraped data, and the project
runs without migration tooling. It covers every franchise that played a
season ending 1991 or later, including the relocations and renames whose
abbreviation changed mid-history (Seattle/OKC, Vancouver/Memphis,
New Jersey/Brooklyn, the Charlotte and New Orleans name churn, the
Washington Bullets).
"""

import re
from datetime import date

# ---------------------------------------------------------------- names

# Name suffixes stripped from the canonical person-name key: sources disagree
# on whether "Gary Trent Jr." carries the suffix at all (ESPN does, the NBA
# stats feed often does not), and a suffix difference must not split one
# person into two.
_SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v", "vi"}


def normalize_name(name):
    """Canonical person-name key: lowercase, punctuation-free, no suffixes.

    Only consistency matters -- "De'Aaron Fox" and "DeAaron Fox" must land on
    the same key, and both sources run the same transform.
    """
    text = str(name or "").lower()
    text = re.sub(r"[.,'’`´\-_()]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    parts = text.split()
    while len(parts) > 1 and parts[-1] in _SUFFIXES:
        parts.pop()
    return " ".join(parts)


# ---------------------------------------------------------------- dates

_MONTHS = {name: i for i, name in enumerate(
    ("january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"), 1)}
_MONTHS.update({name[:3]: i for name, i in list(_MONTHS.items())})

_ISO_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
_LONG_RE = re.compile(r"^([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})$")
_REVERSED_RE = re.compile(r"^(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})$")
_YEAR_RE = re.compile(r"^\d{4}$")


def normalize_date(value):
    """'YYYY-MM-DD' for anything date-shaped, else None.

    Covers the formats the sources actually store: ISO (all three after the
    Eastern-date normalization), ISO with a time/zone suffix (ESPN's
    ``2024-11-13T00:00Z``), ``Month D, YYYY`` (basketball-reference titles
    and player debuts), and ``D Month YYYY``.
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    match = _ISO_RE.search(text)
    if match:
        year, month, day = (int(g) for g in match.groups())
        if 1 <= month <= 12 and 1 <= day <= 31:
            return "%04d-%02d-%02d" % (year, month, day)
        return None
    match = _LONG_RE.match(text)
    if match:
        month = _MONTHS.get(match.group(1).lower())
        if month:
            return "%04d-%02d-%02d" % (
                int(match.group(3)), month, int(match.group(2)))
    match = _REVERSED_RE.match(text)
    if match:
        month = _MONTHS.get(match.group(2).lower())
        if month:
            return "%04d-%02d-%02d" % (
                int(match.group(3)), month, int(match.group(1)))
    return None


def normalize_birthday(value):
    """Birthday key: ISO date when parseable, ``raw:...`` fallback, None if empty.

    basketball-reference stores human dates ("March 3, 1998"), nba.com and
    ESPN store ISO prefixes. An unparseable non-empty value falls back to its
    normalized literal so two sources storing the same odd string still
    match, rather than silently losing the person.
    """
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if not text:
        return None
    iso = normalize_date(text)
    if iso:
        return iso
    return "raw:" + text.lower()


def day_diff(date_a, date_b):
    """Absolute days between two normalized dates; None if either is invalid."""
    if date_a is None or date_b is None:
        return None
    a = date.fromisoformat(date_a)
    b = date.fromisoformat(date_b)
    return abs((a - b).days)


# ---------------------------------------------------------------- locations

# Full state names, so "Los Angeles, CA" and "Los Angeles, California" land
# on the same key. Token-wise replacement: only whole tokens convert, so an
# arena named "... CA ..." (there is none) could not be corrupted.
_STATE_NAMES = {
    "AL": "alabama", "AK": "alaska", "AZ": "arizona", "AR": "arkansas",
    "CA": "california", "CO": "colorado", "CT": "connecticut",
    "DE": "delaware", "DC": "district of columbia", "FL": "florida",
    "GA": "georgia", "HI": "hawaii", "ID": "idaho", "IL": "illinois",
    "IN": "indiana", "IA": "iowa", "KS": "kansas", "KY": "kentucky",
    "LA": "louisiana", "ME": "maine", "MD": "maryland",
    "MA": "massachusetts", "MI": "michigan", "MN": "minnesota",
    "MS": "mississippi", "MO": "missouri", "MT": "montana",
    "NE": "nebraska", "NV": "nevada", "NH": "new hampshire",
    "NJ": "new jersey", "NM": "new mexico", "NY": "new york",
    "NC": "north carolina", "ND": "north dakota", "OH": "ohio",
    "OK": "oklahoma", "OR": "oregon", "PA": "pennsylvania",
    "RI": "rhode island", "SC": "south carolina", "SD": "south dakota",
    "TN": "tennessee", "TX": "texas", "UT": "utah", "VT": "vermont",
    "VA": "virginia", "WA": "washington", "WV": "west virginia",
    "WI": "wisconsin", "WY": "wyoming",
}


def normalize_location(value):
    """Lowercase location with state abbreviations spelled out.

    Game locations agree across sources once the state token is spelled out
    (basketball-reference writes "California", nba.com and ESPN write "CA")
    and once case folds ("crypto.com Arena" vs "Crypto.com Arena").
    """
    text = re.sub(r"\s+", " ", str(value or "")).strip().lower()
    if not text:
        return None
    tokens = []
    for token in text.split():
        bare = token.strip(",.")
        if bare.upper() in _STATE_NAMES:
            tokens.append(token.replace(bare, _STATE_NAMES[bare.upper()]))
        else:
            tokens.append(token)
    return " ".join(tokens)


def location_city(value):
    """City half of a location: team rows disagree on the state suffix.

    basketball-reference team pages store "San Antonio, Texas" while nba.com
    and ESPN store the city only, so team locations compare on the segment
    before the first comma.
    """
    text = re.sub(r"\s+", " ", str(value or "")).strip().lower()
    if not text:
        return None
    return text.split(",")[0].strip() or None


# ---------------------------------------------------------------- franchises

# One entry per franchise: every display name and every abbreviation any
# source has used for it inside the schema's Season window. lookup keys are
# collision-free (asserted by the Phase 2 test suite): two franchises never
# share a name or an abbreviation, so resolution is exact.
FRANCHISES = {
    "hawks":         {"names": ["Atlanta Hawks"],
                      "abbrevs": ["ATL"]},
    "celtics":       {"names": ["Boston Celtics"],
                      "abbrevs": ["BOS"]},
    "nets":          {"names": ["Brooklyn Nets", "New Jersey Nets"],
                      "abbrevs": ["BKN", "BRK", "NJ"]},
    "hornets":       {"names": ["Charlotte Hornets", "Charlotte Bobcats"],
                      "abbrevs": ["CHA", "CHO", "CHH"]},
    "bulls":         {"names": ["Chicago Bulls"],
                      "abbrevs": ["CHI"]},
    "cavaliers":     {"names": ["Cleveland Cavaliers"],
                      "abbrevs": ["CLE"]},
    "mavericks":     {"names": ["Dallas Mavericks"],
                      "abbrevs": ["DAL"]},
    "nuggets":       {"names": ["Denver Nuggets"],
                      "abbrevs": ["DEN"]},
    "pistons":       {"names": ["Detroit Pistons"],
                      "abbrevs": ["DET"]},
    "warriors":      {"names": ["Golden State Warriors"],
                      "abbrevs": ["GSW", "GS"]},
    "rockets":       {"names": ["Houston Rockets"],
                      "abbrevs": ["HOU"]},
    "pacers":        {"names": ["Indiana Pacers"],
                      "abbrevs": ["IND"]},
    "clippers":      {"names": ["Los Angeles Clippers", "LA Clippers"],
                      "abbrevs": ["LAC"]},
    "lakers":        {"names": ["Los Angeles Lakers"],
                      "abbrevs": ["LAL"]},
    "grizzlies":     {"names": ["Memphis Grizzlies",
                                "Vancouver Grizzlies"],
                      "abbrevs": ["MEM", "VAN"]},
    "heat":          {"names": ["Miami Heat"],
                      "abbrevs": ["MIA"]},
    "bucks":         {"names": ["Milwaukee Bucks"],
                      "abbrevs": ["MIL"]},
    "timberwolves":  {"names": ["Minnesota Timberwolves"],
                      "abbrevs": ["MIN"]},
    "pelicans":      {"names": ["New Orleans Pelicans",
                                "New Orleans Hornets",
                                "New Orleans/OKC Hornets"],
                      "abbrevs": ["NOP", "NO", "NOL", "NOK"]},
    "knicks":        {"names": ["New York Knicks"],
                      "abbrevs": ["NYK", "NY"]},
    "thunder":       {"names": ["Oklahoma City Thunder",
                                "Seattle SuperSonics"],
                      "abbrevs": ["OKC", "SEA"]},
    "magic":         {"names": ["Orlando Magic"],
                      "abbrevs": ["ORL"]},
    "sixers":        {"names": ["Philadelphia 76ers"],
                      "abbrevs": ["PHI"]},
    "suns":          {"names": ["Phoenix Suns"],
                      "abbrevs": ["PHX", "PHO"]},
    "trail_blazers": {"names": ["Portland Trail Blazers",
                                "Portland Trailblazers"],
                      "abbrevs": ["POR"]},
    "kings":         {"names": ["Sacramento Kings"],
                      "abbrevs": ["SAC"]},
    "spurs":         {"names": ["San Antonio Spurs"],
                      "abbrevs": ["SAS", "SA"]},
    "raptors":       {"names": ["Toronto Raptors"],
                      "abbrevs": ["TOR"]},
    "jazz":          {"names": ["Utah Jazz"],
                      "abbrevs": ["UTA", "UTH", "UTAH"]},
    "wizards":       {"names": ["Washington Wizards",
                                "Washington Bullets"],
                      "abbrevs": ["WAS", "WSH", "WSB"]},
}

# Reverse lookups, built once. Abbreviations are exact and uppercase;
# names compare on the same whitespace-folded lowercase form the row side
# produces, so "Los Angeles Clippers" and "LA Clippers" are separate keys
# that both resolve.
_BY_ABBREV = {}
_BY_NAME = {}
for _slug, _entry in FRANCHISES.items():
    for _abbrev in _entry["abbrevs"]:
        _BY_ABBREV.setdefault(_abbrev.upper(), _slug)
    for _name in _entry["names"]:
        _BY_NAME.setdefault(re.sub(r"\s+", " ", _name.lower()).strip(), _slug)

BBREF_TEAM_RE = re.compile(r"^/teams/([A-Za-z]{2,4})/")
ESPN_TEAM_RE = re.compile(r"^/espn/team/(\d+)/")
NBA_TEAM_RE = re.compile(r"^/team/(\d+)/")


def resolve_team(href = None, name = None, abbrev = None):
    """Franchise slug for one team row, or None.

    Resolution order: the href's own identifier when it is a
    basketball-reference abbreviation (``/teams/SAS/2025.html``), then the
    row's Abbreviation, then its Name. nba.com and ESPN hrefs carry only
    their opaque numeric ids -- which mean nothing outside their own source
    -- so those fall through to the row fields, which all three sources
    populate with the full city-plus-nickname display name.
    """
    match = BBREF_TEAM_RE.match(str(href or ""))
    if match:
        slug = _BY_ABBREV.get(match.group(1).upper())
        if slug:
            return slug
    if abbrev:
        slug = _BY_ABBREV.get(str(abbrev).strip().upper())
        if slug:
            return slug
    if name:
        return _BY_NAME.get(re.sub(r"\s+", " ", str(name).lower()).strip())
    return None


def alias_token(token):
    """Resolve a user-supplied team token (slug, abbreviation or name)."""
    if token is None:
        return None
    text = str(token).strip()
    if not text:
        return None
    if text in FRANCHISES:
        return text
    slug = _BY_ABBREV.get(text.upper())
    if slug:
        return slug
    return _BY_NAME.get(re.sub(r"\s+", " ", text.lower()).strip())

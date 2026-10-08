# verify.py
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

import scraper
import argparse
import sys
import os
import logging
from scraper.debug import configure
from scraper.verify import Verifier, SECTIONS

desc = """Verify existence and integrity of scraped basketball data.

Read-only by default: prints a report of phantom marks, missing data,
foreign-key orphans, broken invariants, cross-source identity matches
and field-level differences between sources. The only repair flag is
--clear-phantoms, which deletes marks whose claimed data is absent so the
next scrape retries just those."""
parser = argparse.ArgumentParser(prog = "bballVerify",
                                 prefix_chars = "-",
                                 description = desc,
                                 epilog = "")
loc_help = """Location of database. File path for sqlite, otherwise, this should be the
url path to a server."""
parser.add_argument("-o",
                    "--location",
                    required = True,
                    help = loc_help)
db_help = "Type of database to verify."
parser.add_argument("-d",
                    "--db",
                    default = "sqlite",
                    choices = ["sqlite"],
                    # choices = ["sqlite", "mysql", "postgresql"],
                    help = db_help)
only_help = ("Comma-separated subset of sections to run: "
             "phantoms,holes,orphans,invariants,matches,diffs "
             "(default: all).")
parser.add_argument("--only",
                    default = "all",
                    help = only_help)
pairs_help = ("In the matches section, list every confirmed cross-source "
              "pair instead of just the summary count.")
parser.add_argument("--show-pairs",
                    action = "store_true",
                    help = pairs_help)
clear_help = """Delete phantom id_cache marks (and lying game_data marks) so the next
scrape retries just those. A mark whose id still has referencing rows is
never deleted -- re-scraping it would mint a new id and orphan those rows;
it stays in the report as needing the Phase 3 merge."""
parser.add_argument("--clear-phantoms",
                    action = "store_true",
                    help = clear_help)
quiet_help = "Quieter logs: -q keeps warnings and errors, -qq keeps errors only."
parser.add_argument("-q",
                    "--quiet",
                    action = "count",
                    default = 0,
                    help = quiet_help)
verbose_help = "Verbose logs: show per-row detail (cache hits, assumed values)."
parser.add_argument("-v",
                    "--verbose",
                    action = "count",
                    default = 0,
                    help = verbose_help)
args = parser.parse_args(sys.argv[1:])

verbosity = args.verbose - args.quiet
if verbosity >= 1:
    log_level = logging.DEBUG
elif verbosity == 0:
    log_level = logging.INFO
elif verbosity == -1:
    log_level = logging.WARNING
else:
    log_level = logging.ERROR
configure(log_level)


def selected_sections():
    if args.only.strip().lower() == "all":
        return list(SECTIONS)
    chosen = [s.strip() for s in args.only.split(",") if s.strip()]
    if not chosen:
        parser.error("--only needs at least one section")
    for s in chosen:
        if s not in SECTIONS:
            parser.error(f"unknown section {s!r}; choose from "
                         f"{', '.join(SECTIONS)}")
    return chosen


def main():
    if not os.path.isfile(args.location):
        print(f"bballVerify: no such database file: {args.location}",
              file = sys.stderr)
        return 2
    sections = selected_sections()

    db = scraper.dbEngines.get(args.db, scraper.sqlite)(args.location)
    ver = Verifier(db)
    missing = ver.missing_schema()
    if missing:
        print(f"bballVerify: {args.location} is missing tables "
              f"({', '.join(missing)}); run bballInitializeDB first",
              file = sys.stderr)
        ver.close()
        return 2

    if args.clear_phantoms:
        result = ver.clear_phantoms()
        print(f"--clear-phantoms: deleted {len(result['deleted'])} mark(s); "
              f"skipped {len(result['skipped'])} with referencing rows "
              "(see the report)")

    counts = {s: {"finding": 0, "info": 0} for s in SECTIONS}
    for section in sections:
        print(f"== {section} ==")
        if section == "matches":
            rows = ver.matches(show_pairs = args.show_pairs)
        else:
            rows = getattr(ver, section)()
        if not rows:
            print("(clean)")
        for row in rows:
            print(f"[{row['severity'].upper()}] {row['message']}")
            counts[section][row["severity"]] += 1
    ver.close()

    print("== summary ==")
    print(" | ".join(f"{s}: {counts[s]['finding']} finding(s), "
                     f"{counts[s]['info']} info" for s in sections))
    findings = sum(counts[s]["finding"] for s in sections)
    if findings:
        print(f"{findings} finding(s) need attention")
        return 1
    print("clean: no findings")
    return 0


if __name__ == "__main__":
    sys.exit(main())

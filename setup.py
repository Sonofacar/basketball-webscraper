# setup.py
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

from setuptools import setup, find_packages

setup(
    name = "bball-scraper",
    version = "0.0.1",
    description = "Scrape basketball data from a variety of websites.",
    author = "Carson Buttars",
    author_email = "carsonbuttars13@gmail.com",

    #package_dir = {"": "source"},
    packages = find_packages(),

    entry_points = {
        "console_scripts": [
            "bballInitializeDB = scripts.initialize_db:main",
            "bballScrapeYearly = scripts.scrape_yearly:main",
        #     "bball_scrape_daily = scripts.scrape_daily.py:main",
        ],
    },
    # entry_points={
    #     "console_scripts": [
    #         "SwarmScrape = SwarmScrape:run_proxy",
    #     ],
    # },

    install_requires = ["bs4", "requests"],

    classifiers = [
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        #"Operating System :: OS Independent",
    ],
    python_requires = ">=3.6",
)

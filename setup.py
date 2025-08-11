from setuptools import setup, find_packages

setup(
    name = "bball-scraper",  # Fill in your package name
    version = "0.0.1",  # e.g., "0.1.0"
    description = "Scrape basketball data from a variety of websites.",
    author = "Carson Buttars",
    author_email = "carsonbuttars13@gmail.com",

    package_dir = {"": "source"},
    py_modules = ["page_cacher", "debug"],
    packages = find_packages(where="source"),

    entry_points = {
        "console-scripts": [
            "bball_initialize_db = scripts/initialize_db.py:main",
            "bball_scrape_yearly = scripts/scrape_yearly.py:main",
            "bball_scrape_daily = scripts/scrape_daily.py:main",
        ]
    },

    install_requires = ["bs4", "requests"],

    classifiers = [
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        #"Operating System :: OS Independent",
    ],
    python_requires = ">=3.6",
)

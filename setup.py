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
            "bballScrapeYearly = scripts.scrape_yearly.py:main",
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

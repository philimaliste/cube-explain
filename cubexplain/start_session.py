import glob
import json
import os
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Mapping

import atoti as tt
import pandas as pd

from .dataprocessor import DataProcessor

POSTGRES_DATABASE_URL_PATTERN = (
    r"(?P<database>postgres://)(?P<username>.*):(?P<password>.*)@(?P<url>.*)"
)

"""def _get_user_content_storage_config() -> Mapping[str, Mapping[str, str]]:
    database_url = os.environ.get("DATABASE_URL")
    if database_url is None:
        return {}
    match = re.match(POSTGRES_DATABASE_URL_PATTERN, database_url)
    if match is None:
        raise ValueError("Failed to parse database URL")
    username = match.group("username")
    password = match.group("password")
    url = match.group("url")
    if not "postgres" in match.group("database"):
        raise ValueError(f"Expected Postgres database, got {match.group("database")}")
    return {
        "user_content_storage": {
            "url": f"postgresql://{url}?user={username}&password={password}"
        }
    }"""


def start_session(input_path) -> tt.Session:
    session = tt.create_session(
        config={
            **{
                "java_options": ["-Xmx250m"],
                # The $PORT environment variable is used by most PaaS to indicate the port the application server should bind to.
                "port": int(os.environ.get("PORT") or 9090),
            },
            "user_content_storage": "./content",
        }
    )

    print("log path", session.logs_path)

    var_table = session.create_table(
        "Var",
        keys=["Calculation Date", "Scenario", "Book", "Trade Id", "Risk Type"],
        types={
            "Entity": tt.type.STRING,
            "Trade Id": tt.type.INT,
            "Underlier Info": tt.type.STRING,
            "Version": tt.type.INT,
            "Book": tt.type.STRING,
            "Party": tt.type.NULLABLE_STRING,
            "Client Type": tt.type.NULLABLE_STRING,
            "Trader": tt.type.NULLABLE_STRING,
            "Product Type": tt.type.STRING,
            "Description": tt.type.NULLABLE_STRING,
            "Status": tt.type.NULLABLE_STRING,
            "Current Notional": tt.type.FLOAT,
            "Currency": tt.type.NULLABLE_STRING,
            "Parent Entity": tt.type.NULLABLE_STRING,
            "Is Updated Today": tt.type.BOOLEAN,
            "Is Today Trade": tt.type.BOOLEAN,
            "Has Error": tt.type.BOOLEAN,
            "Initial Party": tt.type.NULLABLE_STRING,
            "Csa Desc": tt.type.NULLABLE_STRING,
            "Ccp": tt.type.NULLABLE_STRING,
            "Trading Day": tt.type.NULLABLE_LOCAL_DATE,
            "Input Date": tt.type.NULLABLE_STRING,
            "Update Date": tt.type.NULLABLE_STRING,
            "Maturity Date": tt.type.NULLABLE_STRING,
            "Risk Maturity": tt.type.NULLABLE_STRING,
            "Var": tt.type.FLOAT,
            "Pv": tt.type.FLOAT,
            "IsNewTrade": tt.type.BOOLEAN,
            "Calculation Date": tt.type.LOCAL_DATE,
            "Scenario": tt.type.LOCAL_DATE,
            "Pathfile": tt.type.STRING,
            "Risk Type": tt.type.STRING,
        },
    )

    explain_table = session.create_table(
        "Explain",
        keys=[
            "Calculation Date",
            "Scenario",
            "Book",
            "Product Type",
            "Trade Id",
            "Risk Type",
            "Instrument Underlier Info",
            "Perturbation Type",
            "Curve Delivery Profile",
            "Underlier Tenor",
            "Shock Tenor",
            "Vol Strike",
        ],
        types={
            "Division Id": tt.type.NULLABLE_STRING,
            "Desk Id": tt.type.NULLABLE_STRING,
            "Book": tt.type.STRING,
            "Trade Id": tt.type.INT,
            "Commodity Family": tt.type.NULLABLE_STRING,
            "Commodity Unit Family": tt.type.NULLABLE_STRING,
            "Commodity Long Name": tt.type.NULLABLE_STRING,
            "Commodity Type": tt.type.NULLABLE_STRING,
            "Commodity Reference": tt.type.NULLABLE_STRING,
            "Commodity Lots Size": tt.type.FLOAT,
            "Risk Unit": tt.type.NULLABLE_STRING,
            "Product Type": tt.type.STRING,
            "Instrument Underlier Info": tt.type.STRING,
            "Perturbation Type": tt.type.STRING,
            "Delivery Month": tt.type.NULLABLE_STRING,
            "Delivery Year": tt.type.INT,
            "Delivery Season": tt.type.NULLABLE_STRING,
            "Delivery Quarter": tt.type.NULLABLE_STRING,
            "Volatility Sub Type": tt.type.NULLABLE_STRING,
            "Vol Strike": tt.type.STRING,
            "Underlier Date": tt.type.NULLABLE_LOCAL_DATE,
            "Curve Delivery Profile": tt.type.STRING,
            "Underlier Tenor": tt.type.STRING,
            "Underlier Quote1": tt.type.FLOAT,
            "Underlier Today Quote1": tt.type.FLOAT,
            "Is Today Greeks": tt.type.NULLABLE_BOOLEAN,
            "Explain": tt.type.NULLABLE_FLOAT,
            "Sensitivities": tt.type.NULLABLE_FLOAT,
            "Shock Tenor": tt.type.INT,
            "Calculation Date": tt.type.LOCAL_DATE,
            "Scenario": tt.type.LOCAL_DATE,
            "Pathfile": tt.type.STRING,
            "Risk Type": tt.type.STRING,
        },
    )
    dataprocessor = DataProcessor()
    files = glob.glob(f"{input_path}V@R*.csv")
    print("files ", files)

    with session.start_transaction():
        for file in files:
            print("Loading ", file)
            if "ScenarioDate" in file:
                print("df explain")
                df = dataprocessor.read_explain_file(file)
                print("table explain", len(df))
                explain_table.load_pandas(df)
            else:
                print("df")
                df = dataprocessor.read_var_file(file)
                print("table")
                var_table.load_pandas(df)

    cube = session.create_cube(var_table, mode="no_measures", name="cubexplain")
    m, l, h = cube.measures, cube.levels, cube.hierarchies
    var_table.join(explain_table)
    # Measures
    m["Var.SUM"] = tt.agg.sum(
        tt.agg.sum(var_table["Var"]),
        scope=tt.scope.origin(
            l["Calculation Date"], l["Scenario"], l["Book"], l["Trade Id"]
        ),
    )
    m["Explain.SUM"] = tt.agg.sum(explain_table["Explain"])
    m["Sensi.SUM"] = tt.agg.sum(explain_table["Sensitivities"])
    m["QuoteCentered.MEAN"] = tt.agg.mean(explain_table["Underlier Quote1"])
    m["QuoteShocked.MEAN"] = tt.agg.mean(explain_table["Underlier Today Quote1"])
    m["ShockRelative.MEAN"] = m["QuoteShocked.MEAN"] - m["QuoteCentered.MEAN"]
    m["ShockPercentage.MEAN"] = (m["QuoteShocked.MEAN"] - m["QuoteCentered.MEAN"]) / m[
        "QuoteCentered.MEAN"
    ]
    m["Unexplain.SUM"] = m["Var.SUM"] - m["Explain.SUM"]
    # Polish
    h["Calculation Date"].slicing = True
    h["Scenario"].slicing = True
    m["ShockPercentage.MEAN"].formatter = "DOUBLE[0.00%]"

    @session.endpoint("tables/{table_name}/size", method="GET")
    def get_table_size(request, user, session):
        mdx = "SELECT NON EMPTY Crossjoin([Var].[Calculation Date].[Calculation Date].CURRENTMEMBER, {[Measures].[Explain.SUM]}) ON COLUMNS, NON EMPTY Hierarchize(Descendants({[Var].[Book].[AllMember]}, 1, SELF_AND_BEFORE)) ON ROWS FROM [cubexplain] CELL PROPERTIES VALUE, FORMATTED_VALUE, BACK_COLOR, FORE_COLOR, FONT_FLAGS"
        cube = session.cubes["cubexplain"]
        m = cube.measures
        l = cube.levels
        return session.query_mdx(mdx).to_json()

    @session.endpoint("explain/book", method="POST")
    def mdx(request, user, session):
        return session.cubes["cubexplain"].query(m["Explain.SUM"]).to_json()

    return session

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


def start_session() -> tt.Session:
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
    input_path = "./"
    dataprocessor = DataProcessor()
    files = glob.glob(f"{input_path}V@R*.csv")
    print(files)
    var_df, explain_df = dataprocessor.read_files(files)
    # define Var table
    var_table = session.read_pandas(
        var_df,
        table_name="Var",
        keys=["Calculation Date", "Scenario", "Book", "Trade Id","Risk Type"],
    )
    # define Explain table
    explain_table = session.read_pandas(
        explain_df,
        table_name="Explain",
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
    )
    scenario_table = ["Delta", "Vega", "Gamma"]

    cube = session.create_cube(var_table, mode="no_measures", name="cubexplain")
    m, l, h = cube.measures, cube.levels, cube.hierarchies
    cube.create_parameter_hierarchy_from_members(
        "Sensi Type", scenario_table, index_measure_name="Scenario.INDEX"
    )
    var_table.join(explain_table)
    # Measures
    m["Var.SUM"] = tt.agg.sum(
        tt.agg.sum(var_table["Var"]),
        scope=tt.scope.origin(
            l["Calculation Date"], l["Scenario"], l["Book"], l["Trade Id"]
        ),
    )
    """explain = tt.agg.sum(explain_table["Explain"])
    explain_vector = explain[m["Scenario.INDEX"]]
    explain_alone = tt.array.sum(explain)
    m["Explain.SUM"] = tt.where(explain_vector == None, explain_alone, explain_vector)
    sensi_array = tt.agg.sum(explain_table["Sensitivities"])
    sensi_vector = sensi_array[m["Scenario.INDEX"]]
    sensi_alone = tt.array.sum(sensi_array)
    m["Sensi.SUM"] = tt.where(sensi_vector == None, sensi_alone, sensi_vector)"""
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
    m["Scenario.INDEX"].visible = False

    @session.endpoint("tables/{table_name}/size", method="GET")
    def get_table_size(request, user, session):
        mdx = ("SELECT NON EMPTY Crossjoin([Var].[Calculation Date].[Calculation Date].CURRENTMEMBER, {[Measures].[Explain.SUM]}) ON COLUMNS, NON EMPTY Hierarchize(Descendants({[Var].[Book].[AllMember]}, 1, SELF_AND_BEFORE)) ON ROWS FROM [cubexplain] CELL PROPERTIES VALUE, FORMATTED_VALUE, BACK_COLOR, FORE_COLOR, FONT_FLAGS")
        cube = session.cubes["cubexplain"]
        m = cube.measures
        l = cube.levels
        return session.query_mdx(mdx).to_json()
        #return cube.query(m["Explain.SUM"], levels=[l["Book"]], mode="raw" ).to_json()

    @session.endpoint("explain/book", method="POST")
    def mdx(request, user, session):
        #cube = session.cubes["cubexplain"]
        #m, l, h = cube.measures, cube.levels, cubes.hierarchies
        #levels = request.body["levels"]
        return session.cubes["cubexplain"].query(m["Explain.SUM"]).to_json()

    return session

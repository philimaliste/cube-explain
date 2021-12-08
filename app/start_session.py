import os
import re
from typing import Mapping
import json
from datetime import date, datetime, timedelta
from pathlib import Path

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

    dataprocessor = DataProcessor()
    f = open("./cube_properties.json")
    cube_config = json.load(f)
    input_path = cube_config["path_input"]
    var_files = Path(input_path).glob("*EDEN.csv")
    explain_files = Path(input_path).glob("*ScenarioDate*.csv")
    var_df = dataprocessor.read_var_file(var_files)
    explain_df = dataprocessor.read_explain_file(explain_files)
    var_table = session.read_pandas(
        var_df,
        table_name="Var",
        keys=[
            "Calculation Date",
            "Scenario",
            "Book",
            "Trade Id"
        ]
    )
    explain_table = session.read_pandas(
        explain_df,
        table_name="Explain",
        keys=[
            "Calculation Date",
            "Scenario",
            "Book",
            "Trade Id",
            "Instrument Underlier Info",
            "Perturbation Type",
            "Curve Delivery Profile",
            "Underlier Tenor",
            "Shock Tenor",
            "Vol Strike"
        ]
    )

    scenario_array = ["Delta", "Vega", "Gamma"]

    var_table.join(explain_table)
    cube = session.create_cube(var_table, mode="no_measures")
    cube.create_parameter_hierarchy_from_members(
        "Sensitivities Type", scenario_array, index_measure_name="Scenario.INDEX"
    )
    m = cube.measures
    l = cube.levels
    h = cube.hierarchies
    #Measures
    """measures["VarArray"] = tt.agg.sum(base_table["Risk_histo"])
    measures["Var.VECTOR"] = cube.measures["VarArray"][cube.measures["Scenario.INDEX"]]
    measures["Var.QUANTILE.Alone"] = tt.array.quantile(cube.measures["VarArray"], 0.01, mode="simple", interpolation="midpoint")
    measures["Var.QUANTILE"] = tt.where(cube.measures["Var.VECTOR"] == None,cube.measures["Var.QUANTILE.Alone"],cube.measures["Var.VECTOR"])"""
    m['Var'] = tt.agg.sum(tt.agg.sum(var_table['Var']), scope=tt.scope.origin(l["Calculation Date"], l["Scenario"], l["Book"], l["Trade Id"]))
    m['Var.Explain.Array'] = tt.agg.sum(explain_table['Explain'])
    m["Var.Explain.Vector"] = m['Var.Explain.Array'][m["Scenario.INDEX"]]
    m["Var.Explain.Alone"] = tt.array.sum(m['Var.Explain.Array'])
    m["Var.Explain"] = tt.where(m["Var.Explain.Vector"] == None, m["Var.Explain.Alone"], m["Var.Explain.Vector"])
    m['Sensi.Array'] = tt.agg.sum(explain_table['Sensitivities'])
    m["Sensi.Vector"] = m['Sensi.Array'][m["Scenario.INDEX"]]
    m["Sensi.Alone"] = tt.array.sum(m['Sensi.Array'])
    m["Sensi.Explain"] = tt.where(m["Sensi.Vector"] == None, m["Sensi.Alone"], m["Sensi.Vector"])
    m['Quote.Centered'] = tt.agg.mean(explain_table['Underlier Quote1'])
    m['Quote.Shocked'] = tt.agg.mean(explain_table['Underlier Today Quote1'])
    m['Shock'] = m['Quote.Shocked'] - m['Quote.Centered']
    m['Shock.Raw'] = (m['Quote.Shocked'] - m['Quote.Centered']) / m['Quote.Centered']
    m['Pl'] = tt.agg.mean(tt.agg.sum(explain_table['Pl']), scope = tt.scope.origin(l["Is Today Greeks"]))
    m['DeltaPl'] = tt.agg.mean(tt.agg.sum(explain_table['Delta Pl']), scope=tt.scope.origin(l["Is Today Greeks"]))
    m['VegaPl'] = tt.agg.mean(tt.agg.sum(explain_table['Vega Pl']), scope=tt.scope.origin(l["Is Today Greeks"]))
    m['GammaPl'] = tt.agg.mean(tt.agg.sum(explain_table['Gamma Pl']), scope=tt.scope.origin(l["Is Today Greeks"]))
    m['Delta'] = tt.agg.mean(tt.agg.sum(explain_table['Delta']), scope=tt.scope.origin(l["Is Today Greeks"]))
    m['Vega'] = tt.agg.mean(tt.agg.sum(explain_table['Vega']), scope=tt.scope.origin(l["Is Today Greeks"]))
    m['Gamma'] = tt.agg.mean(tt.agg.sum(explain_table['Gamma']), scope=tt.scope.origin(l["Is Today Greeks"]))
    m['Unexplain'] = m['Var'] - m['Pl']
    #Polish
    h['Calculation Date'].slicing = True
    h['Scenario'].slicing = True
    m['Shock.Raw'].formatter = "DOUBLE[0.00%]"
    """m['Var.Explain.Array'].visible = False
    m["Var.Explain.Vector"].visible = False
    m["Var.Explain.Alone"].visible = False"""
    for measure in [
        m["Pl"],
        m["DeltaPl"],
        m["VegaPl"],
        m["GammaPl"],
        m["Delta"],
        m["Vega"],
        m['Gamma']
    ]:
        measure.folder = "Var.Explain"
    return session

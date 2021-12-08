from datetime import date, datetime, timedelta
import pandas as pd

class DataProcessor:
    def __init__(self) -> None:
        pass


    def read_var_file(self, files) -> pd.DataFrame:
        df = pd.DataFrame()
        for file in files:
            filename = file.stem
            filename_array = filename.split('_')
            calculation_date = datetime.strptime(filename_array[6], '%Y%m%d')
            df_tmp = pd.read_csv(file, parse_dates=['Trading Day'])
            scenario_date = datetime.strptime(df_tmp.columns[-1],'%m/%d/%Y')
            df_tmp = df_tmp.iloc[: , :-1]
            df_tmp = df_tmp.drop(['T:MeteorId', 'Met Prod Type','Meteor Underlying','Folder'], axis=1)
            df_tmp.loc[df_tmp['Trading Day'] == calculation_date, 'IsNewTrade'] = True
            df_tmp.loc[df_tmp['Trading Day'] != calculation_date, 'IsNewTrade'] = False
            df_tmp["Calculation Date"] = calculation_date
            df_tmp["Scenario"] = scenario_date
            df = df.append(df_tmp)
        return df


    def read_explain_file(self, files) -> pd.DataFrame:
        df = pd.DataFrame()
        for file in files:
            filename = file.stem
            filename_array = filename.split('_')
            calculation_date = datetime.strptime(filename_array[6],'%Y%m%d')
            df_tmp = pd.read_csv(file,parse_dates=["Underlier Date"])
            df_tmp['Perturbation Type'] = df_tmp['Perturbation Type'].str.replace("Quote","Fx")
            df_tmp["Explain"] = df_tmp.apply(
                lambda row: [row["Delta Pl"], row["Vega Pl"], row["Gamma Pl"]],
                axis=1
            )
            df_tmp["Sensitivities"] = df_tmp.apply(
                lambda row: [row["Delta"] + row["Today Delta"], row["Vega"] + row["Today Vega"], row["Gamma"] + row["Today Gamma"]],
                 axis=1
            )
            scenario_date = datetime.strptime(filename_array[10],'%Y%m%d')
            df_tmp = df_tmp.rename(columns={'Commodity:Family': 'Commodity Family',
                        'Commodity:Commodity Unit Family':'Commodity Unit Family',
                        'Commodity:Commodity Long Name': 'Commodity Long Name',
                        'Commodity:Commodity Type':'Commodity Type' ,
                        'Commodity:Lots Size': 'Commodity Lots Size',
                        'Commodity:Commodity Reference': 'Commodity Reference' ,
                        'Commodity:Risk Unit': 'Risk Unit',
                        'B:Division Id': 'Division Id',
                        'B:Desk Id': 'Desk Id',
                        'B:GOP Name':'GOP Name'
                        })
            df_tmp['Shock Tenor'] = (df_tmp['Underlier Date'] - calculation_date).dt.days - self._get_tenor_shift(calculation_date)
            df_tmp["Calculation Date"] = calculation_date
            df_tmp["Scenario"] = scenario_date
            df = df.append(df_tmp)
        return df

    def _get_tenor_shift(self, date) -> int:
        weekday = date.strftime("%w")
        yesterday = 1
        if weekday == "5":
            yesterday = 3
        return yesterday

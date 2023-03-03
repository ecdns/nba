import pandas as pd

df = pd.read_csv("nba_games.csv", index_col=0)

# => Trier les lignes avec la date et obtenir les nouevaux index ensuite, sans créer une colonne des anciens index
df.sort_values("date")
df = df.reset_index(drop=True) 

del df["mp.1"]
del df["mp_opp.1"]
del df["index_opp"]

# team = box scores for one team
def add_target(team):
    team["target"] = team["won"].shift(-1)
    return team

df = df.groupby("team", group_keys=False).apply(add_target)

print(df)
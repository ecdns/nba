import pandas as pd

df = pd.read_csv("nba_games.csv", index_col=0)

print(df)
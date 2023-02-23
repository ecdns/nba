import requests
import pandas as pd
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np

year = 2022

# URL DE LA REQUETE GET
url = "https://www.basketball-reference.com/leagues/NBA_2023.html"

# REQUETE GET
data = requests.get(url)

# INSERTION DU HMTL RECUPERE
with open('teamsStats.html', "w+") as f:
    f.write(data.text)

# STOCKAGE DANS VARIABLE PAGE
with open("teamsStats.html") as f:
    page = f.read()

# EXTRACTION DU TABLEAU
soup = BeautifulSoup(page, "html.parser")
table = soup.find(id="per_game-team")

# PASSAGE D'UNE SIMPLE STRING EN DATAFRAME AVEC PANDAS
perGameStatTable = pd.read_html(str(table))[0]
perGameStatTable.drop('FT', inplace=True, axis=1)
perGameStatTable.drop('FTA', inplace=True, axis=1)
perGameStatTable.drop('FT%', inplace=True, axis=1)

perGameStatTable = perGameStatTable.rename(columns={'Rk': 'Rank','G': 'Games', 'MP': 'Minutes', 'FG': 'Goals', 'FGA': 'Attempts', 'FG%': 'Success', 'ORB': 'Reb.off', 'DRB': 'Reb.def', 'TRB': 'Reb.total', 'STL': 'Steals', 'BLK': 'Block', 'TOV': 'Turnover', 'PF': 'Foules'})

def perGameSuccessGraph():
    plt.bar(perGameStatTable['Team'], perGameStatTable['Success'], color = cm.rainbow(np.linspace(0, 1, len(perGameStatTable['Team']))))
    plt.xticks(rotation=90)
    plt.ylim([min(perGameStatTable['Success']), max(perGameStatTable['Success'])])
    return plt.show()

def perGameRebGraph():
    plt.bar(perGameStatTable['Team'], +perGameStatTable['Reb.off'], facecolor='#9999ff', edgecolor='white')
    plt.bar(perGameStatTable['Team'], -perGameStatTable['Reb.def'], facecolor='#ff9999', edgecolor='white')
    plt.show()


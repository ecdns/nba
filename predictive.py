import pandas as pd
from sklearn.model_selection import TimeSeriesSplit # Découper une série temporelle en prenant en compte la dépendance temporelle
from sklearn.feature_selection import SequentialFeatureSelector # Sélectionner de manière séquentielle un sous ensemble de caractéristiques à partie d'un ensemble plus large
from sklearn.linear_model import RidgeClassifier # Fonction linéaire régularisée, prédire la classe d'un échantillon à partir de caractéristiques
from sklearn.preprocessing import MinMaxScaler 

###################################### TRAITEMENT DE DONNEES ##########################################

df = pd.read_csv("nba_games.csv", index_col=0)

# => Trier les lignes avec la date et obtenir les nouevaux index ensuite, sans créer une colonne des anciens index
df = df.sort_values("date")
df = df.reset_index(drop=True) 

del df["mp.1"]
del df["mp_opp.1"]
del df["index_opp"]

# team = box scores for one team
# add_target => inclue une colonne indiquant le résultat de l'équipe au match d'après
def add_target(team):
    team["target"] = team["won"].shift(-1)
    return team

df = df.groupby("team", group_keys=False).apply(add_target)
df["target"][pd.isnull(df["target"])] = 2
df["target"] = df["target"].astype(int, errors="ignore")

team_df = df[df["team"] == "WAS"]

# Checker toutes les valeurs nulles de notre dataframe : false si c'est not null, true si c'est null
nulls = pd.isnull(df).sum()
nulls = nulls[nulls > 0]
# Sélection des colonnes qui ne sont pas dans nulls grâce à l'opérateur négatif ~
valid_columns = df.columns[~df.columns.isin(nulls.index)]
# Permet de copier les nouvelles colonnes, les ajouter dans des colonnes existantes peuvent créer des erreurs
df = df[valid_columns].copy()

##################################################### MACHINE LEARNING #################################################################

# Traiter un grand nombre de colonnes en machine learning peut entraîner des erreurs de corrélations, utilisation de sélecteurs
# Machine learning model
rr = RidgeClassifier(alpha=1) # Alpha pour la régularisation
split = TimeSeriesSplit(n_splits = 3)

# Le sélecteur va entraîner la machine en envoyant des parties de features et récupérer les features les plus pertinentes
sfs = SequentialFeatureSelector(rr, n_features_to_select=30, direction="forward", cv=split)

removed_columns = ["season", "date", "won", "target", "team", "team_opp"]

selected_columns = df.columns[~df.columns.isin(removed_columns)]
# Valeurs des colonnes sélectionnées sont entre 0 et 1
scaler = MinMaxScaler()
df[selected_columns] = scaler.fit_transform(df[selected_columns])

# Récupérer les 30 meilleures features pour prédire
sfs.fit(df[selected_columns], df["target"])

# sfs.get_support => True: colonnes pertinentes pour notre prédiction
predictors = list(selected_columns[sfs.get_support()])
print(sfs.get_support())
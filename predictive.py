import pandas as pd
from sklearn.model_selection import \
    TimeSeriesSplit  # Découper une série temporelle en prenant en compte la dépendance temporelle
from sklearn.feature_selection import \
    SequentialFeatureSelector  # Sélectionner de manière séquentielle un sous ensemble de caractéristiques à partie d'un ensemble plus large
from sklearn.linear_model import \
    RidgeClassifier  # Fonction linéaire régularisée, prédire la classe d'un échantillon à partir de caractéristiques
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import accuracy_score

###################################### TRAITEMENT DE DONNEES ##########################################

df = pd.read_csv("nba_games.csv", index_col=0)

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
rr = RidgeClassifier(alpha=1)  # Alpha pour la régularisation
split = TimeSeriesSplit(n_splits=3)

# Le sélecteur va entraîner la machine en envoyant des parties de features et récupérer les features les plus pertinentes
sfs = SequentialFeatureSelector(rr, n_features_to_select=30, direction="forward", cv=split)

removed_columns = ["season", "date", "won", "target", "team", "team_opp"]

selected_columns = df.columns[~df.columns.isin(removed_columns)]
# Valeurs des colonnes sélectionnées sont entre 0 et 1
scaler = MinMaxScaler()
df[selected_columns] = scaler.fit_transform(df[selected_columns])

# Récupérer les 30 meilleures features pour prédire les labels
sfs.fit(df[selected_columns], df["target"])

# sfs.get_support => True: colonnes pertinentes pour notre prédiction
predictors = list(selected_columns[sfs.get_support()])

def backtest(data, model, predictors, date):
    all_predictions = []

    train = data[data["date"] < date]
    model.fit(train[predictors], train["target"])

    preds = model.predict(data[predictors])
    preds = pd.Series(preds, index=data.index)

    combined = pd.concat([data["target"], preds], axis=1)
    combined.columns = ["actual", "prediction"]

    all_predictions.append(combined)
    return pd.concat(all_predictions)

# Récupérer les colonnes sélectionnées et ajouter les colonnes won et team
df_rolling = df[list(selected_columns) + ["won", "team"]]

# Groupe les 10 dernières lignes d'une équipe de notre df, pour chacune des lignes, retourne la moyenne avec mean
def find_team_averages(team):
    rolling = team.rolling(50).mean()
    return rolling
# Regrouper nos colonnes pour une équipe spécifique
df_rolling = df_rolling.groupby(["team"], group_keys = False).apply(find_team_averages)

rolling_cols = [f"{col}_10" for col in df_rolling.columns]
df_rolling.columns = rolling_cols

df = pd.concat([df, df_rolling], axis=1)
df = df.dropna()

def shift_col(team, col_name):
    next_col = team[col_name].shift(-1)
    return next_col

def add_col(df, col_name):
    return df.groupby("team", group_keys=False).apply(lambda x: shift_col(x, col_name))

df["home_next"] = add_col(df, "home")
df["team_opp_next"] = add_col(df, "team_opp")
df["date_next"] = add_col(df, "date")
df = df.copy()

full = df.merge(df[rolling_cols + ["team_opp_next", "date_next", "team"]],
                left_on=["team", "date_next"],
                right_on=["team_opp_next", "date_next"]
)

removed_columns = list(full.columns[full.dtypes == "object"]) + removed_columns
selected_columns = full.columns[~full.columns.isin(removed_columns)]

sfs.fit(full[selected_columns], full["target"])
predictions = backtest(full, rr, predictors, "2023-03-11")
accuracy = accuracy_score(predictions["actual"], predictions["prediction"])

full = pd.concat([full, predictions], axis=1)

myDfPrediction = full.loc[:, ["team_x", "team_opp", "won", "home", "date", "won_10_y", "team_opp_next_x", "prediction", "target"]]


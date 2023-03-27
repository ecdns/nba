from bs4 import BeautifulSoup
import pandas as pd
from selenium import webdriver
import os
import time
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
import asyncio
import csv

DATA_DIR = "data"
STANDINGS_DIR = os.path.join(DATA_DIR, "standings")
SCORES_DIR = os.path.join(DATA_DIR, "scores")
box_scores = os.listdir(SCORES_DIR)
box_scores = [os.path.join(SCORES_DIR, f) for f in box_scores if f.endswith(".html")]

async def get_html(url, selector, sleep=5, retries=3):
    html = None
    for i in range(1, retries+1):
        time.sleep(sleep * i)
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                page = await browser.new_page()
                await page.goto(url, timeout=0)
                html = await page.inner_html(selector)
        except PlaywrightTimeout:
            print(f"Timeout")
            continue
        else:
            break
    return html

async def scrape_season():
    url = "https://www.basketball-reference.com/leagues/NBA_2023_games.html"
    html = await get_html(url, "#content .filter")

    soup = BeautifulSoup(html, "html.parser")
    # Chaque mois de la saison
    links = soup.find_all("a")
    # Liste avec les liens de chacun des mois
    href = [l["href"] for l in links]
    # Chaque page de résultats de chaque mois
    standings_pages = [f"https://basketball-reference.com{l}" for l in href]
    for url in standings_pages:
        # Rajout du mois dans le lien du fichier
        save_path = os.path.join(STANDINGS_DIR, url.split("/")[-1])
        html = await get_html(url, "#all_schedule")
        with open(save_path, "w+") as f:
            f.write(html)

async def scrape_game(standings_file):

    with open(standings_file, "r") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    # Tous les liens de la page de résultats pour octobre
    links = soup.find_all('a')

    hrefs = [l.get("href") for l in links]
    box_scores = [l for l in hrefs if l and "boxscore" in l and ".html" in l]
    # Obtenir tous les liens des box scores
    box_scores = [f"https://www.basketball-reference.com{l}" for l in box_scores]

    for url in box_scores:
        save_path = os.path.join(SCORES_DIR, url.split("/")[-1])
        if(os.path.exists(save_path)):
            continue
        html = await get_html(url, "#content")
        if not html:
            continue
        with open(save_path, "w+") as f:
            f.write(html)
            
#Parser le tableau de box score
def parse_html(box_score):
    with open(box_score) as f:
        html = f.read()

    soup = BeautifulSoup(html, "html5lib")
    [s.decompose() for s in soup.select("tr.over_header")]
    [s.decompose() for s in soup.select("tr.thead")]

    return soup
# Lire la ligne du score du tableau
def read_line_score(soup):
    line_score = pd.read_html(str(soup), attrs={"id": "line_score"})[0]
    cols = list(line_score.columns)
    cols[0] = "team"
    cols[-1] = "total"
    line_score.columns = cols
    return line_score
# Lire les stats d'une des deux équipes de la rencontre
def read_stats(soup, team, stat):
    df = pd.read_html(str(soup), attrs={"id": f"box-{team}-game-{stat}"}, index_col=0)[0]
    df = df.apply(pd.to_numeric, errors="coerce")
    return df

def update():
    standings_files = os.listdir(STANDINGS_DIR)
    asyncio.run(scrape_season())
    # Parcourir chaque mois de la saison
    standings_files = [s for s in standings_files if '.html' in s]
    for f in standings_files:
        filepath = os.path.join(STANDINGS_DIR, f)
        asyncio.run(scrape_game(filepath))

def getAllStats():
    games = []
    base_cols = None

    for box_score in box_scores:
        print(os.path.basename(box_score))
        soup = parse_html(box_score)
        line_score = read_line_score(soup)
        teams = list(line_score["team"])

        summaries = []
        for team in teams:
            basic = read_stats(soup, team, "basic")
            advanced = read_stats(soup, team, "advanced")

            totals = pd.concat([basic.iloc[-1,:], advanced.iloc[-1,:]]) 
            totals.index = totals.index.str.lower()

            # Maximums de chacunes des colonnes des tableaux basic et advance 
            maxes = pd.concat([basic.iloc[:-1,:].max(), advanced.iloc[:-1,:].max()])
            maxes.index = maxes.index.str.lower() + "_max"
            summary = pd.concat([totals, maxes])

            if(base_cols is None):
                # Supprime les colonnes qui sont identiques (mp)
                base_cols = list(summary.index.drop_duplicates(keep="first"))
                # bpm est dans certaines box scores mais pas dans d'autres
                base_cols = [b for b in base_cols if "bpm" not in b]

            summary = summary[base_cols]
            summaries.append(summary)
        # Concaténer dans un summary seul
        summary = pd.concat(summaries, axis=1).T

        #Nouvelle colonne dans summary -> axis 1 colonne
        game = pd.concat([summary, line_score[["team", "total"]]], axis=1)
        game["home"] = [0, 1]
        # Utiliser des nouveaux index
        game_opp = game.iloc[::-1].reset_index()
        game_opp.columns += "_opp"

        full_game = pd.concat([game, game_opp], axis=1)

        full_game["date"] = os.path.basename(box_score)[:8]
        full_game["date"] = pd.to_datetime(full_game["date"], format="%Y%m%d")

        full_game["won"] = full_game["total"] > full_game["total_opp"]
        games.append(full_game)

        if len(games) % 100 == 0:
            print(f"{len(games)} / {len(box_scores)}")
    # → Trier les lignes avec la date et obtenir les nouveaux index ensuite, sans créer une colonne des anciens index
    games_df = pd.concat(games, ignore_index=True).sort_values("date").reset_index(drop=True)
    games_df.to_csv("nba_games.csv")

update()
getAllStats()
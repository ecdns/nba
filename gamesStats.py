from bs4 import BeautifulSoup
import pandas as pd
from selenium import webdriver
import os
import time
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
import asyncio

DATA_DIR = "data"
STANDINGS_DIR = os.path.join(DATA_DIR, "standings")
SCORES_DIR = os.path.join(DATA_DIR, "scores")
standings_files = os.listdir(STANDINGS_DIR)

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
    url = f"https://www.basketball-reference.com/leagues/NBA_2023_games.html"
    html = await get_html(url, "#content .filter")

    soup = BeautifulSoup(html, "html.parser")
    links = soup.find_all("a")
    # Création d'une nouvelle liste href à partir de toutes les valeurs des clés href de la liste links
    href = [l["href"] for l in links]

    standings_pages = [f"https://basketball-reference.com{l}" for l in href]
    for url in standings_pages:
        print (url)
        #liaison de deux chemins pour former le chemin du répertoire dans lequel nous enregistrons la page scrappée
        save_path = os.path.join(STANDINGS_DIR, url.split("/")[-1])
        if os.path.exists(save_path):
            continue
        html = await get_html(url, "#all_schedule")
        with open(save_path, "w+") as f:
            f.write(html)

async def scrape_game(standings_file):
    standings_file = standings_files[6]

    with open(f"data/standings/{standings_file}", "r") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    links = soup.find_all('a')

    hrefs = [l.get("href") for l in links]
    box_scores = [l for l in hrefs if l and "boxscore" in l and ".html" in l]
    box_scores = [f"https://www.basketball-reference.com{l}" for l in box_scores]

    for url in box_scores:
        save_path = os.path.join(SCORES_DIR, url.split("/")[-1])
        if(os.path.exists(save_path)):
            continue
        with open(save_path, "w+") as f:
            f.write(html)
            
#Parser le tableau de box score
def parse_html(box_score):
    with open(box_score) as f:
        html = f.read()

    soup = BeautifulSoup(html, 'html.parse')
    [s.decompose() for s in soup.select("tr.over_header")]
    [s.decompose() for s in soup.select("tr.thead")]

    return soup
# Lire la ligne du score du tableau
def read_line_score(soup):
    line_score = pd.read_html(str(soup), attrs={"id": "line_score"})[0]
    cols = list(line_score.columns)
    cols[0] = "team"
    cols[-1] = "total"
    line_score = line_score[["team"], ["total"]]
    return line_score

# Parcourir chaque mois de la saison
standings_files = [s for s in standings_files if('.html') in s]
for f in standings_files:
    filepath = os.path.join(STANDINGS_DIR, f)
    asyncio.run(scrape_game(filepath))

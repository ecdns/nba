from bs4 import BeautifulSoup
import pandas as pd
from selenium import webdriver
import os
import time

chrome_driver = os.path.abspath(os.path.dirname(__file__)) + '/chromedriver'
browser = webdriver.Chrome(chrome_driver)
url = "https://www.basketball-reference.com/leagues/NBA_2023_per_game.html"
browser.get(url)
browser.execute_script("window.scrollTo(1,10000)")
time.sleep(2)
html = browser.page_source
with open("playersStats.html", "w+") as f:
    f.write(html)

with open("playersStats.html") as f:
    page = f.read()

soup = BeautifulSoup(page, "html.parser")
soup.find('tr', class_="thead").decompose()
table = soup.find(id="per_game_stats")

dataFrame = pd.read_html(str(table))[0]
print (dataFrame)
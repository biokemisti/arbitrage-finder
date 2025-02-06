import requests
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

url = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds"

params = {
    "apiKey": os.getenv("ODDS_API_KEY"),
    "regions": "eu",
    "markets": "h2h,totals",
}

response = requests.get(url, params=params)

if response.status_code == 200:
    odds_data = response.json()
else:
    print(f"Failed to fetch data: {response.status_code}")
    odds_data = []

games_list = []


def implied_probability(odds):
    return 1 / odds if odds else 0


for game in odds_data:
    game_info = {
        "commence_time": game["commence_time"],
        "home_team": game["home_team"],
        "away_team": game["away_team"],
        "odds": {},
        "arbitrage_h2h": False,
        "arbitrage_totals": False,
        "arbitrage_bets": {},
    }

    best_home_odds = 0
    best_away_odds = 0
    best_over_odds = 0
    best_under_odds = 0
    home_bet_bookmaker = ""
    away_bet_bookmaker = ""
    over_bet_bookmaker = ""
    under_bet_bookmaker = ""

    for bookmaker in game["bookmakers"]:
        bookmaker_name = bookmaker["title"]
        game_info["odds"][bookmaker_name] = {
            "h2h": {
                "home_odds": None,
                "away_odds": None,
            },
            "totals": {
                "over_odds": None,
                "under_odds": None,
                "total_points": None,
            },
        }

        for market in bookmaker["markets"]:
            if market["key"] == "h2h":
                for outcome in market["outcomes"]:
                    if outcome["name"] == game["home_team"]:
                        game_info["odds"][bookmaker_name]["h2h"]["home_odds"] = outcome[
                            "price"
                        ]
                        if outcome["price"] > best_home_odds:
                            best_home_odds = outcome["price"]
                            home_bet_bookmaker = bookmaker_name
                    elif outcome["name"] == game["away_team"]:
                        game_info["odds"][bookmaker_name]["h2h"]["away_odds"] = outcome[
                            "price"
                        ]
                        if outcome["price"] > best_away_odds:
                            best_away_odds = outcome["price"]
                            away_bet_bookmaker = bookmaker_name

            elif market["key"] == "totals":
                for outcome in market["outcomes"]:
                    if outcome["name"] == "Over":
                        game_info["odds"][bookmaker_name]["totals"]["over_odds"] = (
                            outcome["price"]
                        )
                        if outcome["price"] > best_over_odds:
                            best_over_odds = outcome["price"]
                            over_bet_bookmaker = bookmaker_name
                        game_info["odds"][bookmaker_name]["totals"]["total_points"] = (
                            outcome["point"]
                        )
                    elif outcome["name"] == "Under":
                        game_info["odds"][bookmaker_name]["totals"]["under_odds"] = (
                            outcome["price"]
                        )
                        if outcome["price"] > best_under_odds:
                            best_under_odds = outcome["price"]
                            under_bet_bookmaker = bookmaker_name

    home_prob = implied_probability(best_home_odds)
    away_prob = implied_probability(best_away_odds)
    over_prob = implied_probability(best_over_odds)
    under_prob = implied_probability(best_under_odds)

    arbitrage_h2h = home_prob + away_prob < 1
    arbitrage_totals = over_prob + under_prob < 1

    if arbitrage_h2h or arbitrage_totals:
        game_info["arbitrage_bets"] = {
            "h2h": {
                "home": {"odds": best_home_odds, "bookmaker": home_bet_bookmaker},
                "away": {"odds": best_away_odds, "bookmaker": away_bet_bookmaker},
            },
            "totals": {
                "over": {"odds": best_over_odds, "bookmaker": over_bet_bookmaker},
                "under": {"odds": best_under_odds, "bookmaker": under_bet_bookmaker},
            },
        }

    game_info["arbitrage_h2h"] = arbitrage_h2h
    game_info["arbitrage_totals"] = arbitrage_totals
    game_info["arbitrage_h2h_prob_sum"] = home_prob + away_prob
    game_info["arbitrage_totals_prob_sum"] = over_prob + under_prob

    games_list.append(game_info)

df = pd.DataFrame(games_list)

df["commence_time"] = pd.to_datetime(df["commence_time"])

arbitrage_games = df[(df["arbitrage_h2h"] == True) | (df["arbitrage_totals"] == True)]

with open("arbitrage_opportunities.txt", "w") as file:
    file.write("Games with Arbitrage Opportunities:\n")
    for index, game in arbitrage_games.iterrows():
        file.write(f"\n{game['home_team']} vs {game['away_team']}\n")
        file.write(f"{game['commence_time'].strftime('%Y-%m-%d %H:%M:%S')}\n")
        file.write(f"Arbitrage H2H: {game['arbitrage_h2h']}\n")
        file.write(f"Arbitrage Totals: {game['arbitrage_totals']}\n")
        file.write(f"Sum of H2H Probabilities: {game['arbitrage_h2h_prob_sum']:.4f}\n")
        file.write(
            f"Sum of Totals Probabilities: {game['arbitrage_totals_prob_sum']:.4f}\n"
        )
        file.write("Arbitrage Bets:\n")
        file.write(f"  H2H - Home: {game['arbitrage_bets']['h2h']['home']}\n")
        file.write(f"       Away: {game['arbitrage_bets']['h2h']['away']}\n")
        file.write(f"  Totals - Over: {game['arbitrage_bets']['totals']['over']}\n")
        file.write(f"          Under: {game['arbitrage_bets']['totals']['under']}\n")
        file.write("\n")

print("Arbitrage opportunities saved to 'arbitrage_opportunities.txt'")

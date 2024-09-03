import numpy as np
import pandas as pd

from basketball_reference_web_scraper import client

import time

def get_player_statistics(season_end_year):
    """Return a DataFrame of a season stats for all players
    using basketball reference web scraper
    """
    results = client.players_season_totals(season_end_year=season_end_year)
    for result in results:
        result["team"] = result["team"].value
    return pd.DataFrame.from_dict(results)


def calculate_turnover(gb, year1=2000, year2=2001):
    """turnover is defined as sum of the
    absolute difference between mintues played
    for each player from the two seasons.

    :param gb: A pandas groupby dataframe
    """
    s1 = gb.loc[gb["year"] == year1]
    s1.set_index("slug", inplace=True)

    s2 = gb.loc[gb["year"] == year2]
    s2.set_index("slug", inplace=True)

    combined = s1.join(s2, how="outer", lsuffix="_year1", rsuffix="_year2").fillna(0)
    turnover = np.abs(combined["minutes_played_year2"] - combined["minutes_played_year1"]).sum()
    return turnover


if __name__ == "__main__":
    # This DataFrame will store minutes played information for every player
    player_minutes = pd.DataFrame()
    # This DataFrame will be used to store team name, year, win total, and roster turnover
    roster_turnover = pd.DataFrame()
    # hold the correlation values between wins and turnover for a given year
    wins_turnover_corr = {}

    years = range(2004, 2025)
    for year in years:
        wins_df = pd.DataFrame(client.standings(season_end_year=year))
        wins_df = wins_df[["team", "wins"]]
        wins_df["team"] = wins_df["team"].apply(lambda x: x.name.replace("_", " "))
        wins_df.set_index("team", inplace=True)

        # scrape season stats for every NBA player for the previous year
        previous_season = get_player_statistics(year - 1)
        previous_season["year"] = year - 1

        # scrape season stats for every NBA player for the current year
        current_season = get_player_statistics(year)
        current_season["year"] = year

        # combine the season stats into one DataFrame
        combined = pd.concat([previous_season, current_season])
        # add minutes played to the larger player_minutes DataFrame
        player_minutes = pd.concat([player_minutes, combined[["team", "name", "slug", "minutes_played", "year"]]])

        # GroupBy the teams to calculate how much roster turnover there is from year to year.
        gb = combined.groupby("team")
        turnover_df = pd.DataFrame(
            gb.apply(calculate_turnover, year1=year - 1, year2=year),
            columns=["turnover"],
        )

        # join the calculated turnover with the scraped wins totals
        turnover_df = turnover_df.join(wins_df)
        turnover_df["year"] = year

        roster_turnover = pd.concat([roster_turnover, turnover_df])

        # calculate the correlation between wins and roster turnover
        wins_turnover_corr[year] = turnover_df.corr()["wins"]["turnover"]

        print(f"Finished {year} season")
        time.sleep(10)

    # always write these to file, because the kernel self-references it's output
    player_minutes = player_minutes.drop_duplicates()
    player_minutes.to_csv("data/NBA_player_minutes.2004-2024.csv")
    roster_turnover.to_csv("data/NBA_roster_turnover_wins.2004-2024.csv")

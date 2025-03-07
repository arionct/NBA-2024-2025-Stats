import os
import csv
import statistics
import math
from collections import defaultdict
from datetime import datetime
import xlsxwriter

DATE_FORMAT = "%m/%d/%Y"

def parse_all_team_files(directory):
    """
    Reads all 3-letter .txt files in 'directory' (e.g. ATL.txt, BOS.txt).
    Returns a dict:
       player_data[player_name] = {
           "points": [float, float, ...],
           "most_recent_date": datetime object or None,
           "current_team": str or None
       }
    """
    player_data = defaultdict(lambda: {
        "points": [],
        "most_recent_date": None,
        "current_team": None
    })

    for filename in os.listdir(directory):
        # only process files named like: 3 letters + ".txt"
        if filename.endswith(".txt") and len(filename) == 7:
            filepath = os.path.join(directory, filename)
            with open(filepath, 'r', encoding='utf-8', newline='') as csvfile:
                reader = csv.DictReader(csvfile, delimiter='\t')
                for row in reader:
                    player_name = row.get('PLAYER')
                    pts_str = row.get('PTS')
                    date_str = row.get('GAME DATE')
                    team_str = row.get('TEAM')

                    if not player_name or not pts_str or not date_str or not team_str:
                        continue

                    # convert pts to float
                    try:
                        points = float(pts_str)
                    except ValueError:
                        continue

                    # parse date
                    try:
                        game_date = datetime.strptime(date_str, DATE_FORMAT)
                    except ValueError:
                        continue

                    # add to player's points
                    player_data[player_name]["points"].append(points)

                    # check if this game is more recent than the stored one
                    current_recent = player_data[player_name]["most_recent_date"]
                    if current_recent is None or game_date > current_recent:
                        player_data[player_name]["most_recent_date"] = game_date
                        player_data[player_name]["current_team"] = team_str

    return player_data

def percentile(sorted_list, pct):
    """
    Returns the percentile value from 'sorted_list' for the given 'pct' in [0,1].
    Example: pct=0.10 for 10th percentile.
    """
    n = len(sorted_list)
    if n == 0:
        return None
    if n == 1:
        return sorted_list[0]

    index = (n - 1) * pct
    lower_idx = int(math.floor(index))
    upper_idx = int(math.ceil(index))

    if lower_idx == upper_idx:
        return sorted_list[lower_idx]

    lower_val = sorted_list[lower_idx]
    upper_val = sorted_list[upper_idx]
    frac = index - lower_idx
    return lower_val + (upper_val - lower_val) * frac

def lower_semideviation(points):
    if not points:
        return 0.0
    
    n = len(points)
    mu = sum(points) / n
    
    # filter out only the observations below the mean
    below_mean = [p for p in points if p < mu]
    
    if len(below_mean) <= 1:
        return 0.0
    
    # compute semivariance
    squared_diffs = [(mu - p)**2 for p in below_mean]
    semivariance = sum(squared_diffs) / len(below_mean)
    
    # return the square root of semivariance
    return math.sqrt(semivariance)

def main():
    directory = "./Box scores by team"
    data = parse_all_team_files(directory)

    results = []
    for player, info in data.items():
        pts_list = info["points"]
        current_team = info["current_team"]
        games_played = len(pts_list)
        
        if games_played == 0:
            continue
        
        mean_pts = sum(pts_list) / games_played
        std_dev = lower_semideviation(pts_list)
        cv = std_dev / mean_pts if abs(mean_pts) > 1e-9 else 0.0
        
        sorted_pts = sorted(pts_list)
        p10 = percentile(sorted_pts, 0.10)
        p20 = percentile(sorted_pts, 0.20)
        p30 = percentile(sorted_pts, 0.30)

        results.append((player, current_team, mean_pts, std_dev, cv, p10, p20, p30, games_played))
    
    # sort by ascending standard deviation
    results.sort(key=lambda x: x[3])

    # print to console with one-decimal rounding
    print(f"{'Player':25s}  {'Team':5s}  {'PPG':>5s}  {'StdDev':>6s}  {'CV':>4s}  {'P10':>5s}  {'P20':>5s}  {'P30':>5s}  {'Games':>5s}")
    print("-" * 90)
    for (player, team, mean_pts, std_dev, cv, p10, p20, p30, games_played) in results:
        print(f"{player:25s}"
              f"  {team:5s}"
              f"  {mean_pts:5.1f}"
              f"  {std_dev:6.1f}"
              f"  {cv:4.1f}"
              f"  {p10:5.1f}"
              f"  {p20:5.1f}"
              f"  {p30:5.1f}"
              f"  {games_played:5d}")

    # export to Excel
    workbook = xlsxwriter.Workbook("player_stats.xlsx")
    worksheet = workbook.add_worksheet("Player Stats")

    headers = ["Player", "Current Team", "PPG", "Std Dev", "CV", "10th Pctl", "20th Pctl", "30th Pctl", "Games"]
    for col_idx, header in enumerate(headers):
        worksheet.write(0, col_idx, header)

    row = 1
    for (player, team, mean_pts, std_dev, cv, p10, p20, p30, games_played) in results:
        worksheet.write(row, 0, player)
        worksheet.write(row, 1, team)
        worksheet.write(row, 2, round(mean_pts, 1))
        worksheet.write(row, 3, round(std_dev, 1))
        worksheet.write(row, 4, round(cv, 1))
        worksheet.write(row, 5, round(p10, 1) if p10 is not None else None)
        worksheet.write(row, 6, round(p20, 1) if p20 is not None else None)
        worksheet.write(row, 7, round(p30, 1) if p30 is not None else None)
        worksheet.write(row, 8, games_played)
        row += 1

    workbook.close()
    print("\nData exported to player_stats.xlsx")

if __name__ == "__main__":
    main()

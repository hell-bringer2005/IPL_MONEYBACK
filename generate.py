import zipfile
import json
import pandas as pd
import os

# --- CONFIGURATION ---
ZIP_FILE_PATH = 'Archive.zip'
PROFILE_CSV_PATH = 'people.csv'
OUTPUT_CSV_PATH = 'season_data.csv'

def get_empty_season_stats():
    return {
        'matches': 0,
        'innings_batted': 0,
        'runs_scored': 0,
        'balls_faced': 0,
        'fours': 0,
        'sixes': 0,
        'not_outs': 0,
        'high_score': 0,
        'centuries': 0,
        'fifties': 0,
        'innings_bowled': 0,
        'balls_bowled': 0,
        'runs_conceded': 0,
        'wickets': 0,
        'catches': 0,
        'stumpings': 0
    }

def process_season_stats():
    print(f"Reading {ZIP_FILE_PATH}...")
    
    # Key: (Season, Player Name) -> Stats Dict
    season_stats = {}

    with zipfile.ZipFile(ZIP_FILE_PATH, 'r') as z:
        json_files = [f for f in z.namelist() if f.endswith('.json')]
        total_files = len(json_files)
        
        for i, filename in enumerate(json_files):
            if i % 100 == 0: print(f"Processing {i}/{total_files}...")
            
            with z.open(filename) as f:
                try:
                    match_data = json.load(f)
                except:
                    continue

                if 'innings' not in match_data or 'info' not in match_data:
                    continue
                
                # Get Season (Clean it up, e.g., "2007/08" -> "2008")
                raw_season = str(match_data['info'].get('season', 'Unknown'))
                # Simple cleaning: take the first 4 digits if it looks like a year
                season = raw_season.split('/')[0] if '/' in raw_season else raw_season

                players_in_match = set()

                for inning in match_data['innings']:
                    if 'overs' not in inning: continue
                    
                    for over in inning['overs']:
                        for ball in over['deliveries']:
                            batter = ball['batter']
                            bowler = ball['bowler']
                            players_in_match.add(batter)
                            players_in_match.add(bowler)

                            # Init Stats
                            if (season, batter) not in season_stats: season_stats[(season, batter)] = get_empty_season_stats()
                            if (season, bowler) not in season_stats: season_stats[(season, bowler)] = get_empty_season_stats()

                            # --- BATTING ---
                            s_bat = season_stats[(season, batter)]
                            runs_bat = ball['runs']['batter']
                            s_bat['runs_scored'] += runs_bat
                            
                            if runs_bat == 4: s_bat['fours'] += 1
                            if runs_bat == 6: s_bat['sixes'] += 1
                            
                            # Legal balls for SR
                            if 'wides' not in ball.get('extras', {}):
                                s_bat['balls_faced'] += 1

                            # --- BOWLING ---
                            s_bowl = season_stats[(season, bowler)]
                            # Runs conceded (Total - Byes/Legbyes)
                            extras = ball.get('extras', {})
                            deduct = extras.get('byes', 0) + extras.get('legbyes', 0) + extras.get('penalty', 0)
                            s_bowl['runs_conceded'] += (ball['runs']['total'] - deduct)
                            
                            if 'wides' not in extras and 'noballs' not in extras:
                                s_bowl['balls_bowled'] += 1

                            # --- WICKETS & FIELDING ---
                            if 'wickets' in ball:
                                for w in ball['wickets']:
                                    kind = w['kind']
                                    player_out = w['player_out']

                                    # Batting: Out?
                                    # (Complex to track "not outs" perfectly in this simplified loop, 
                                    #  but we can count dismissals to calc avg later)
                                    
                                    # Bowling Wicket
                                    if kind not in ['run out', 'retired hurt', 'obstructing the field']:
                                        s_bowl['wickets'] += 1
                                    
                                    # Fielding
                                    if 'fielders' in w:
                                        for fielder in w['fielders']:
                                            fname = fielder['name']
                                            players_in_match.add(fname)
                                            if (season, fname) not in season_stats: 
                                                season_stats[(season, fname)] = get_empty_season_stats()
                                            
                                            if kind == 'caught':
                                                season_stats[(season, fname)]['catches'] += 1
                                            elif kind == 'stumped':
                                                season_stats[(season, fname)]['stumpings'] += 1
                                    
                                    if kind == 'caught and bowled':
                                        s_bowl['catches'] += 1

                # Count Matches
                for p in players_in_match:
                    if (season, p) not in season_stats: season_stats[(season, p)] = get_empty_season_stats()
                    season_stats[(season, p)]['matches'] += 1

    # --- EXPORT ---
    print("Exporting...")
    data = []
    for (season, name), stats in season_stats.items():
        row = stats.copy()
        row['season'] = season
        row['name'] = name
        data.append(row)
    
    df = pd.DataFrame(data)
    
    # Merge Profiles (Optional)
    try:
        profiles = pd.read_csv(PROFILE_CSV_PATH)
        df = pd.merge(df, profiles, on='name', how='left')
    except:
        pass

    df.to_csv(OUTPUT_CSV_PATH, index=False)
    print(f"Done! Saved to {OUTPUT_CSV_PATH}")

if __name__ == "__main__":
    process_season_stats()
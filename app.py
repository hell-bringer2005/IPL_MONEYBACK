import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="IPL Moneyball: Premium Analytics",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    :root {
        --primary-color: #1f77b4;
        --secondary-color: #ff7f0e;
        --success-color: #2ecc71;
        --danger-color: #e74c3c;
        --warning-color: #f39c12;
        --dark-bg: #0e1117;
        --card-bg: #161b22;
        --border-color: #30363d;
        --text-primary: #f0f2f6;
        --text-secondary: #8b949e;
    }
    
    .stApp { background-color: #0e1117; }
    
    h1, h2, h3, h4 { color: #f0f2f6; font-family: 'Inter', sans-serif; }
    
    .metric-card {
        background: linear-gradient(135deg, #161b22 0%, #0d1117 100%);
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 20px;
        margin: 10px 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        transition: transform 0.2s;
        min-height: 140px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .metric-card:hover { transform: translateY(-2px); border-color: #58a6ff; }
    
    .stat-value { font-size: 28px; font-weight: 700; color: #58a6ff; }
    .stat-label { font-size: 13px; color: #8b949e; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px; }
    
    .role-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 12px;
        margin-top: 5px;
    }
    .role-batter { background-color: rgba(31, 119, 180, 0.2); color: #4fa8df; border: 1px solid #1f77b4; }
    .role-bowler { background-color: rgba(231, 76, 60, 0.2); color: #ff8a80; border: 1px solid #e74c3c; }
    .role-allrounder { background-color: rgba(243, 156, 18, 0.2); color: #fcd581; border: 1px solid #f39c12; }
    
    .chart-container {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 20px;
        margin: 15px 0;
    }
    
    [data-testid="stSidebar"] { background-color: #0d1117; border-right: 1px solid #30363d; }
    
    .price-highlight { font-size: 32px; font-weight: 700; color: #2ecc71; margin: 10px 0; }
    .price-delta-up { color: #2ecc71; font-size: 14px; }
    .price-delta-down { color: #e74c3c; font-size: 14px; }
    
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def load_dashboard_data():
    # 1. Load Season Data (Ball-by-ball aggregated)
    try:
        df = pd.read_csv('season_data.csv')
        df['season'] = df['season'].astype(str)
    except FileNotFoundError:
        return None, None

    # Calculate Season Metrics
    df['batting_avg'] = df.apply(lambda x: x['runs_scored'] / (x['matches'] - x['not_outs']) if (x['matches'] - x['not_outs']) > 0 else x['runs_scored'], axis=1)
    df['batting_sr'] = df.apply(lambda x: (x['runs_scored'] / x['balls_faced']) * 100 if x['balls_faced'] > 0 else 0, axis=1)
    df['bowling_economy'] = df.apply(lambda x: x['runs_conceded'] / (x['balls_bowled']/6) if x['balls_bowled'] > 0 else 0, axis=1)

    # 2. Load Master Data (For accurate 100s, 50s, 4s, 6s, 5w)
    try:
        master_data = pd.read_csv('master_data.csv')
        # Ensure we have the specific columns needed
        cols_to_merge = ['name', 'centuries', 'fifties', 'sixes', 'fours', '5_wickets']
        master_subset = master_data[cols_to_merge].copy()
    except (FileNotFoundError, KeyError):
        master_subset = pd.DataFrame(columns=['name', 'centuries', 'fifties', 'sixes', 'fours', '5_wickets'])

    # 3. Aggregation
    sum_cols = ['matches', 'runs_scored', 'balls_faced', 'wickets', 'balls_bowled', 'runs_conceded', 'catches']
    career_df = df.groupby('name')[sum_cols].sum().reset_index()

    # 4. Merge Correct Stats from Master Data
    # We drop these columns if they exist in career_df to avoid duplication before merge
    for c in ['centuries', 'fifties', 'sixes', 'fours', '5_wickets']:
        if c in career_df.columns:
            career_df.drop(columns=[c], inplace=True)
            
    if not master_subset.empty:
        career_df = pd.merge(career_df, master_subset, on='name', how='left')
        # Fill NaNs with 0 for players present in season data but not master data
        career_df[['centuries', 'fifties', 'sixes', 'fours', '5_wickets']] = career_df[['centuries', 'fifties', 'sixes', 'fours', '5_wickets']].fillna(0)
    else:
        # Fallback if master_data isn't found
        career_df['centuries'] = 0
        career_df['fifties'] = 0
        career_df['sixes'] = 0
        career_df['fours'] = 0
        career_df['5_wickets'] = 0

    # Career Derived Metrics
    career_df['batting_avg'] = round(career_df['runs_scored'] / career_df['matches'], 2) 
    career_df['batting_sr'] = career_df.apply(lambda x: round((x['runs_scored'] / x['balls_faced']) * 100, 2) if x['balls_faced'] > 0 else 0, axis=1)
    career_df['bowling_economy'] = career_df.apply(lambda x: round(x['runs_conceded'] / (x['balls_bowled']/6), 2) if x['balls_bowled'] > 0 else 0, axis=1)
    career_df['all_rounder_score'] = career_df['runs_scored'] + (career_df['wickets'] * 25)

    # Normalize for Radar
    for col in ['batting_avg', 'batting_sr', 'runs_scored', 'wickets']:
        max_val = career_df[col].quantile(0.99)
        if max_val == 0: max_val = 1
        career_df[f'norm_{col}'] = (career_df[col] / max_val).clip(0, 1)
    
    career_df['norm_bowling_economy'] = 1 - ((career_df['bowling_economy'] - 5) / (12 - 5)).clip(0, 1)

    return df, career_df

@st.cache_data
def load_ml_data():
    try:
        master_df = pd.read_csv('IPL_Master_Player_Data copy.csv')
        stats_df = pd.read_csv('cricket_data copy.csv')
        
        master_df['Price'] = pd.to_numeric(master_df['Price'], errors='coerce').fillna(0)
        master_df['Year'] = pd.to_numeric(master_df['Year'], errors='coerce')
        master_df = master_df.dropna(subset=['Year'])
        master_df = master_df[master_df['Price'] > 0]

        stats_df['Year'] = pd.to_numeric(stats_df['Year'], errors='coerce')
        stats_df = stats_df.dropna(subset=['Year'])
        
        cols_to_clean = ['Runs_Scored', 'Wickets_Taken', 'Batting_Strike_Rate',
                        'Bowling_Average', 'Economy_Rate', 'Matches_Batted']
        for col in cols_to_clean:
            if col in stats_df.columns:
                stats_df[col] = pd.to_numeric(
                    stats_df[col].astype(str).str.replace(r'[^\d.]', '', regex=True),
                    errors='coerce'
                ).fillna(0)

        master_df['join_name'] = master_df['Player'].str.lower().str.strip()
        stats_df['join_name'] = stats_df['Player_Name'].str.lower().str.strip()
        
        return master_df, stats_df
        
    except FileNotFoundError:
        return None, None

season_df, career_df = load_dashboard_data()
df_master, df_stats = load_ml_data()

def calculate_valuation(runs, wickets, matches, last_price=0):
    IDEAL_BAT_RUNS = 973.0
    IDEAL_BOWL_WKTS = 32.0
    IDEAL_AR_RUNS = 510.0
    IDEAL_AR_WKTS = 11.0
    MAX_PRICE_CAP = 210000000.0

    is_bowler = (wickets >= 12) or (wickets > matches * 0.8) if matches > 0 else False
    is_allrounder = (runs > 200) and (wickets >= 6)
    
    role = "Batter"
    perf_ratio = 0.0

    if is_allrounder:
        role = "All-Rounder"
        bat_ratio = min(runs / IDEAL_AR_RUNS, 1.2) if IDEAL_AR_RUNS > 0 else 0
        bowl_ratio = min(wickets / IDEAL_AR_WKTS, 1.2) if IDEAL_AR_WKTS > 0 else 0
        perf_ratio = (bat_ratio * 0.6) + (bowl_ratio * 0.4)
    elif is_bowler:
        role = "Bowler"
        perf_ratio = min(wickets / IDEAL_BOWL_WKTS, 1.1) if IDEAL_BOWL_WKTS > 0 else 0
    else:
        role = "Batter"
        perf_ratio = min(runs / IDEAL_BAT_RUNS, 1.1) if IDEAL_BAT_RUNS > 0 else 0

    base_perf_price = perf_ratio * MAX_PRICE_CAP
    
    if last_price > 0:
        final_price = (0.70 * last_price) + (0.30 * base_perf_price)
    else:
        final_price = base_perf_price * 0.85
        
    return final_price, role, perf_ratio * 100

def format_price(price):
    if price >= 10000000: return f"₹ {price/10000000:.2f} Cr"
    elif price >= 100000: return f"₹ {price/100000:.2f} L"
    else: return f"₹ {price:,.0f}"

def render_metric_card(label, value, icon=""):
    st.markdown(f"""
    <div class="metric-card">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div class="stat-label">{label}</div>
            <div style="font-size: 20px;">{icon}</div>
        </div>
        <div class="stat-value">{value}</div>
    </div>
    """, unsafe_allow_html=True)

with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/en/thumb/8/84/Indian_Premier_League_Official_Logo.svg/1200px-Indian_Premier_League_Official_Logo.svg.png", width=120)
    st.title("IPL Premium")
    st.caption("Advanced Analytics Dashboard")
    st.markdown("---")
    
    view_mode = st.radio(
        "Navigation", 
        ["👤 Player 360° Profile", "🏆 Hall of Fame", "🤖 ML Valuation Engine"]
    )
    st.markdown("---")

if view_mode == "👤 Player 360° Profile":
    
    if season_df is None:
        st.error("Missing `season_data.csv`")
        st.stop()

    player_list = sorted(career_df['name'].unique())
    selected_player = st.sidebar.selectbox("🔍 Select Player", player_list)
    
    p_career = career_df[career_df['name'] == selected_player].iloc[0]
    p_season = season_df[season_df['name'] == selected_player].sort_values('season')

    col1, col2 = st.columns([1, 4])
    with col1:
        st.markdown(f"<div style='font-size: 60px; text-align: center;'>🏏</div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<h1 style='margin-bottom: 5px;'>{selected_player}</h1>", unsafe_allow_html=True)
        if p_career['all_rounder_score'] > 2000 and p_career['wickets'] > 10:
            badge_cls, badge_txt = "role-allrounder", "ALL-ROUNDER"
        elif p_career['wickets'] > p_career['matches']:
            badge_cls, badge_txt = "role-bowler", "BOWLER"
        else:
            badge_cls, badge_txt = "role-batter", "BATTER"
            
        st.markdown(f"""
            <span class='role-badge {badge_cls}'>{badge_txt}</span>
            <span style='color: #8b949e; margin-left: 10px;'>Matches: {p_career['matches']} • Active Seasons: {len(p_season)}</span>
        """, unsafe_allow_html=True)
    
    st.markdown("---")

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: render_metric_card("Runs", f"{int(p_career['runs_scored']):,}", "🏃")
    with c2: render_metric_card("Wickets", f"{int(p_career['wickets'])}", "🎯")
    with c3: render_metric_card("Batting Avg", f"{p_career['batting_avg']}", "📊")
    with c4: render_metric_card("Strike Rate", f"{p_career['batting_sr']}", "⚡")
    with c5: render_metric_card("Economy", f"{p_career['bowling_economy']}", "💰")

    m1, m2, m3 = st.columns(3)
    
    centuries = int(p_career.get('centuries', 0))
    fifties = int(p_career.get('fifties', 0))
    five_wickets = int(p_career.get('5_wickets', 0))

    with m1: render_metric_card("Centuries", f"{centuries}", "💯")
    with m2: render_metric_card("Half Centuries", f"{fifties}", "5️⃣")
    with m3: render_metric_card("5-Wicket Hauls", f"{five_wickets}", "🖐️")

    st.markdown("### 📊 Performance Analytics")
    tab1, tab2 = st.tabs(["📈 Career Trajectory", "🕸️ Skill Radar"])
    
    with tab1:
        with st.container():
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            col_chart1, col_chart2 = st.columns(2)
            
            with col_chart1:
                fig_runs = go.Figure()
                fig_runs.add_trace(go.Bar(
                    x=p_season['season'], y=p_season['runs_scored'],
                    name='Runs', marker=dict(color=p_season['runs_scored'], colorscale='Blues', showscale=False)
                ))
                fig_runs.update_layout(title='Runs per Season', height=600, template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_runs, use_container_width=True)
                
            with col_chart2:
                fig_wkts = go.Figure()
                fig_wkts.add_trace(go.Bar(
                    x=p_season['season'], y=p_season['wickets'],
                    name='Wickets', marker=dict(color=p_season['wickets'], colorscale='Reds', showscale=False)
                ))
                fig_wkts.update_layout(title='Wickets per Season', height=600, template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_wkts, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        col_rad1, col_rad2 = st.columns([2, 1])
        with col_rad1:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            categories = ['Consistency', 'Aggression', 'Volume', 'Wicket Taking', 'Economy (Inv)']
            values = [p_career['norm_batting_avg'], p_career['norm_batting_sr'], p_career['norm_runs_scored'], p_career['norm_wickets'], p_career['norm_bowling_economy']]
            fig_radar = go.Figure(go.Scatterpolar(r=values, theta=categories, fill='toself', name=selected_player, line_color='#2ecc71'))
            fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 1], color='#8b949e')), showlegend=False, height=600, template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', title="360° Skill Assessment")
            st.plotly_chart(fig_radar, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col_rad2:
            st.markdown("#### Run Composition")
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            labels = ['Fours', 'Sixes', 'Running']
            
            fours_count = p_career.get('fours', 0)
            sixes_count = p_career.get('sixes', 0)
            total_runs = p_career.get('runs_scored', 0)
            
            run_4s = fours_count * 4
            run_6s = sixes_count * 6
            run_run = total_runs - (run_4s + run_6s)
            
            vals = [run_4s, run_6s, run_run]
            fig_pie = go.Figure(go.Pie(labels=labels, values=vals, hole=.4, marker_colors=['#3498DB', '#E74C3C', '#F1C40F']))
            fig_pie.update_layout(height=600, margin=dict(t=0,b=0,l=0,r=0), template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_pie, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

elif view_mode == "🏆 Hall of Fame":
    
    if season_df is None:
        st.error("Missing `season_data.csv`")
        st.stop()

    st.title("🏆 IPL Hall of Fame")
    htab1, htab2, htab3 = st.tabs(["🏏 Top Batters", "🎯 Top Bowlers", "🔥 MVPs"])
    
    with htab1:
        top_runs = career_df.sort_values('runs_scored', ascending=False).head(10)
        fig = px.bar(top_runs, x='runs_scored', y='name', orientation='h', color='batting_sr', color_continuous_scale='OrRd', title="Highest Run Scorers")
        fig.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', yaxis={'categoryorder':'total ascending'}, height=700)
        st.plotly_chart(fig, use_container_width=True)
        
    with htab2:
        top_wkts = career_df.sort_values('wickets', ascending=False).head(10)
        fig = px.bar(top_wkts, x='wickets', y='name', orientation='h', color='bowling_economy', color_continuous_scale='Tealgrn_r', title="Highest Wicket Takers")
        fig.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', yaxis={'categoryorder':'total ascending'}, height=700)
        st.plotly_chart(fig, use_container_width=True)
        
    with htab3:
        top_ar = career_df.sort_values('all_rounder_score', ascending=False).head(15)
        fig = px.scatter(top_ar, x='runs_scored', y='wickets', size='all_rounder_score', color='name', title="The Elite Club (Batting vs Bowling Impact)")
        fig.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', height=700)
        st.plotly_chart(fig, use_container_width=True)

elif view_mode == "🤖 ML Valuation Engine":
    
    if df_stats is None or df_master is None:
        st.error("⚠️ Missing Uploaded Data: `cricket_data copy.csv` or `IPL_Master_Player_Data copy.csv`")
        st.stop()

    st.title("🤖 ML Valuation Engine")
    st.markdown("Predict a player's auction value based on performance metrics.")
    
    st.subheader("1. Select Base Profile")
    ml_players = sorted(df_stats['Player_Name'].unique())
    val_player = st.selectbox("Search Player Database", ["Custom Profile"] + list(ml_players))
    
    d_runs, d_wkts, d_match = 400, 10, 14
    last_known_price = 0
    price_lbl = "N/A"

    if val_player != "Custom Profile":
        p_stats = df_stats[df_stats['Player_Name'] == val_player].sort_values('Year')
        if not p_stats.empty:
            latest = p_stats.iloc[-1]
            d_runs = int(latest['Runs_Scored'])
            d_wkts = int(latest['Wickets_Taken'])
            d_match = int(latest['Matches_Batted'])
        
        m_entry = df_master[df_master['join_name'] == val_player.lower().strip()]
        if not m_entry.empty:
            last_known_price = m_entry.sort_values('Year').iloc[-1]['Price']
            price_lbl = format_price(last_known_price)

    st.subheader("2. Configure Performance (What-If Analysis)")
    with st.container():
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        col_in1, col_in2, col_in3 = st.columns(3)
        with col_in1: i_runs = st.slider("Runs Scored (Season)", 0, 1000, d_runs)
        with col_in2: i_wkts = st.slider("Wickets Taken (Season)", 0, 50, d_wkts)
        with col_in3: i_matches = st.slider("Matches Played", 1, 17, d_match)
        st.markdown('</div>', unsafe_allow_html=True)

    final_val, role, perf_score = calculate_valuation(i_runs, i_wkts, i_matches, last_price=last_known_price)
    
    st.markdown("---")
    col_res1, col_res2, col_res3 = st.columns(3)
    
    with col_res1:
        st.markdown(f"""
            <div class='metric-card'>
                <div class='stat-label'>IDENTIFIED ROLE</div>
                <div style='margin-top: 10px;'>
                    <span class='role-badge role-{role.lower().replace(" ", "")}'>{role.upper()}</span>
                </div>
                <div class='stat-label' style='margin-top: 20px;'>PERFORMANCE SCORE</div>
                <div class='stat-value'>{perf_score:.1f}%</div>
            </div>
        """, unsafe_allow_html=True)

    with col_res2:
        val_fmt = format_price(final_val)
        diff_html = ""
        if last_known_price > 0:
            diff = final_val - last_known_price
            d_fmt = format_price(abs(diff))
            if diff > 0: diff_html = f"<div class='price-delta-up'>⬆ +{d_fmt} vs Last Price</div>"
            else: diff_html = f"<div class='price-delta-down'>⬇ -{d_fmt} vs Last Price</div>"

        st.markdown(f"""
            <div class='metric-card'>
                <div class='stat-label'>ESTIMATED VALUATION</div>
                <div class='price-highlight'>{val_fmt}</div>
                {diff_html}
            </div>
        """, unsafe_allow_html=True)
        
    with col_res3:
        st.markdown(f"""
            <div class='metric-card'>
                <div class='stat-label'>LAST AUCTION PRICE</div>
                <div class='stat-value' style='color: #fbbf24;'>{price_lbl}</div>
                <div class='stat-label' style='margin-top: 12px;'>Market Reference</div>
            </div>
        """, unsafe_allow_html=True)
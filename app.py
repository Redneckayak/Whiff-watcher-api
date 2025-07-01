import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
import numpy as np

from mlb_api import MLBDataFetcher
from data_processor import DataProcessor
from predictor import StrikeoutPredictor

# Configure page
st.set_page_config(
    page_title="Whiff Watcher - MLB Strikeout Predictions",
    page_icon="⚾",
    layout="wide"
)

# Initialize components
@st.cache_resource
def get_components():
    fetcher = MLBDataFetcher()
    processor = DataProcessor()
    predictor = StrikeoutPredictor()
    return fetcher, processor, predictor

def main():
    st.title("⚾ Whiff Watcher")
    st.subheader("MLB Strikeout Prediction Analytics")
    st.markdown("*Predicting strikeouts by analyzing pitcher-batter matchups with 20%+ strikeout rates*")
    
    # Get components
    try:
        fetcher, processor, predictor = get_components()
    except Exception as e:
        st.error(f"Failed to initialize application components: {str(e)}")
        return
    
    # Sidebar for controls
    with st.sidebar:
        st.header("Controls")
        
        # Date selector (default to today)
        selected_date = st.date_input(
            "Select Date",
            value=date.today(),
            help="Choose the date for MLB games analysis"
        )
        
        # At-bats filter
        min_at_bats = st.number_input(
            "Min At-Bats",
            min_value=0,
            max_value=600,
            value=200,
            step=50,
            help="Filter batters by minimum at-bats for meaningful stats"
        )
        
        # Refresh button
        if st.button("🔄 Refresh Data", help="Fetch latest MLB data"):
            st.cache_data.clear()
            st.rerun()
    
    # Main content
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        st.metric("Date", selected_date.strftime("%B %d, %Y"))
    
    # Fetch today's games
    with st.spinner("Fetching MLB games data..."):
        try:
            games_data = fetcher.get_todays_games(selected_date)
            
            if not games_data:
                st.warning(f"No MLB games found for {selected_date.strftime('%B %d, %Y')}")
                st.info("Note: MLB regular season typically runs April-September. Try a date from the 2024 season (April-September) to see sample data.")
                return
                
            with col2:
                st.metric("Games Today", len(games_data))
            
            # Show debug info about games and roster sizes
            with st.expander("Debug: Games & Roster Info", expanded=False):
                st.write(f"Found {len(games_data)} games with probable pitchers")
                for i, game in enumerate(games_data[:3]):
                    away_pitcher = game.get('away_pitcher', {}).get('name', 'TBD') if game.get('away_pitcher') else 'TBD'
                    home_pitcher = game.get('home_pitcher', {}).get('name', 'TBD') if game.get('home_pitcher') else 'TBD'
                    st.text(f"{game['away_team']} ({away_pitcher}) @ {game['home_team']} ({home_pitcher})")
                    
                    # Show roster sizes for debugging
                    away_team_id = fetcher.get_team_id_by_name(game['away_team'])
                    home_team_id = fetcher.get_team_id_by_name(game['home_team'])
                    if away_team_id:
                        away_roster = fetcher.get_team_roster(away_team_id)
                        st.text(f"  {game['away_team']} roster: {len(away_roster)} batters")
                    if home_team_id:
                        home_roster = fetcher.get_team_roster(home_team_id)
                        st.text(f"  {game['home_team']} roster: {len(home_roster)} batters")
                
        except Exception as e:
            st.error(f"Failed to fetch games data: {str(e)}")
            st.info("Please check your internet connection and try again.")
            return
    
    # Process matchups
    with st.spinner("Analyzing pitcher-batter matchups..."):
        try:
            all_matchups = []
            
            for game in games_data:
                game_matchups = processor.process_game_matchups(game, fetcher, min_at_bats)
                all_matchups.extend(game_matchups)
                st.write(f"Debug: {game['away_team']} @ {game['home_team']} generated {len(game_matchups)} matchups")
            
            st.write(f"Debug: Total matchups before filtering: {len(all_matchups)}")
            
            if not all_matchups:
                st.warning("No matchup data available for the selected date.")
                return
                
            # Convert to DataFrame
            matchups_df = pd.DataFrame(all_matchups)
            
            with col3:
                st.metric("Total Matchups", len(matchups_df))
                
        except Exception as e:
            st.error(f"Failed to process matchup data: {str(e)}")
            return
    
    # Display simple matchups table
    st.markdown("---")
    st.markdown("### Today's Pitcher vs Batter Matchups")
    
    if not matchups_df.empty:
        # Create simple table with combined strikeout percentages
        display_df = matchups_df.copy()
        
        # Calculate combined strikeout percentage (simple addition)
        display_df['combined_so_rate'] = display_df['batter_so_rate'] + display_df['pitcher_so_rate']
        
        # Select only the essential columns
        simple_df = display_df[[
            'batter_name', 'batter_so_rate', 'pitcher_name', 'pitcher_so_rate', 'combined_so_rate'
        ]].copy()
        
        # Round to 1 decimal place
        simple_df['batter_so_rate'] = simple_df['batter_so_rate'].round(1)
        simple_df['pitcher_so_rate'] = simple_df['pitcher_so_rate'].round(1)
        simple_df['combined_so_rate'] = simple_df['combined_so_rate'].round(1)
        
        # Sort by combined strikeout rate (highest first) 
        simple_df = simple_df.iloc[simple_df['combined_so_rate'].argsort()[::-1]].reset_index(drop=True)
        
        # Check for and remove duplicates before renaming
        initial_count = len(simple_df)
        simple_df = simple_df.drop_duplicates(subset=['batter_name'], keep='first')
        final_count = len(simple_df)
        
        if initial_count != final_count:
            st.warning(f"Removed {initial_count - final_count} duplicate batter entries")
        
        # Rename columns
        simple_df.columns = ['Batter', 'Batter K%', 'Pitcher', 'Pitcher K%', 'Combined K%']
        
        # Display the table
        st.dataframe(
            simple_df,
            use_container_width=True,
            hide_index=True
        )
        
        # Add data verification section
        with st.expander("Verify Player Data", expanded=False):
            st.write("Raw statistics for verification:")
            if len(matchups_df) > 0:
                # Show raw data for verification
                verification_df = matchups_df[['batter_name', 'batter_strikeouts', 'batter_at_bats', 'batter_so_rate']].drop_duplicates()
                verification_df['Calculated K%'] = (verification_df['batter_strikeouts'] / verification_df['batter_at_bats'] * 100).round(1)
                verification_df = verification_df.rename(columns={
                    'batter_name': 'Player',
                    'batter_strikeouts': 'Strikeouts',
                    'batter_at_bats': 'At Bats',
                    'batter_so_rate': 'Our K%'
                })
                st.dataframe(verification_df.head(10), use_container_width=True)
                st.write("Compare 'Our K%' with 'Calculated K%' - they should match if calculation is correct")
        
        st.info(f"Showing {len(simple_df)} unique matchups (batters with {min_at_bats}+ at-bats) sorted by highest combined strikeout percentage")
    else:
        st.info("No matchup data available for the selected date.")
    
    # Footer with data info
    st.markdown("---")
    st.markdown("**Data Sources:** MLB Stats API | **Last Updated:** " + datetime.now().strftime("%I:%M %p %Z"))
    st.markdown("*Predictions are based on historical data and should be used for entertainment purposes only.*")





if __name__ == "__main__":
    main()

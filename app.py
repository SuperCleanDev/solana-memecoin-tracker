"""
بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ
Streamlit Web App - Your Control Center
May Allah grant success to this project
"""

import streamlit as st
from datetime import datetime, timedelta, time
import json
import os
from bitquery_client import BitqueryClient
from processor import TokenProcessor
import config

# Page config
st.set_page_config(
    page_title="Solana Memecoin Tracker",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# PASSWORD PROTECTION
def check_password():
    """Returns True if user entered correct password"""
    
    def password_entered():
        """Checks whether password is correct"""
        if st.session_state["password"] == st.secrets.get("APP_PASSWORD", "bismillah2025"):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show password input
        st.text_input(
            "🔐 Enter Password", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        st.info("Enter the app password to continue")
        return False
    elif not st.session_state["password_correct"]:
        # Password incorrect
        st.text_input(
            "🔐 Enter Password", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        st.error("❌ Incorrect password")
        return False
    else:
        # Password correct
        return True

if not check_password():
    st.stop()

# Custom CSS for mobile responsiveness
st.markdown("""
<style>
    .main > div {
        padding-top: 2rem;
    }
    .stButton button {
        width: 100%;
        height: 3rem;
        font-size: 1.2rem;
        font-weight: bold;
    }
    @media (max-width: 768px) {
        .stButton button {
            height: 2.5rem;
            font-size: 1rem;
        }
        .main > div {
            padding-top: 1rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# Title
st.title("🚀 Solana Memecoin Tracker")
st.markdown("**Track Pump.fun launches with accurate on-chain data**")
st.markdown("*بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ*")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Time range preset
    preset = st.selectbox(
        "Quick Select",
        list(config.TIME_RANGE_PRESETS.keys()),
        index=0
    )
    
    preset_config = config.TIME_RANGE_PRESETS[preset]
    st.info(preset_config['description'])
    
    # Date selection
    st.subheader("📅 Select Date")
    selected_date = st.date_input(
        "Date",
        value=datetime.now() - timedelta(days=3),
        min_value=datetime(2024, 1, 1),
        max_value=datetime.now()
    )
    
    # Time selection
    if preset == 'Custom':
        col1, col2 = st.columns(2)
        with col1:
            start_time = st.time_input("From (UTC)", value=time(0, 0, 0))
        with col2:
            end_time = st.time_input("To (UTC)", value=time(23, 59, 59))
    else:
        start_time_str = preset_config['start']
        end_time_str = preset_config['end']
        start_time = datetime.strptime(start_time_str, "%H:%M:%S").time()
        end_time = datetime.strptime(end_time_str, "%H:%M:%S").time()
        st.info(f"⏰ {start_time_str} to {end_time_str} UTC")
    
    # Combine date and time
    start_datetime = datetime.combine(selected_date, start_time)
    end_datetime = datetime.combine(selected_date, end_time)
    
    st.markdown("---")
    
    # Show criteria (DYNAMIC from config)
    min_roi = config.SUCCESSFUL_TOKEN_CONFIG['min_roi_multiplier']
    min_peak_mc = config.SUCCESSFUL_TOKEN_CONFIG['min_peak_mc']
    tracking_hours = config.ANALYSIS_WINDOW['tracking_duration_hours']
    
    st.subheader("✅ Success Criteria")
    st.markdown(f"""
    - Peak MC ≥ **${min_peak_mc:,}**
    - ROI ≥ **{min_roi}x** from $25K
    - Entry window: Launch to $25K MC
    - Tracking: **{tracking_hours} hours** from launch
    """)
    
    st.subheader("❌ Failure Criteria")
    st.markdown("""
    - **Pump & Dump:** Pumped to $15K-$100K, tanked 80%+
    - **Rug Pull:** Liquidity pulled (<$5K)
    """)
    
    st.markdown("---")
    
    # API Key
    bitquery_token = st.text_input(
        "Bitquery API Token",
        type="password",
        value=st.secrets.get("BITQUERY_API_TOKEN", ""),
        help="Get free token from https://graphql.bitquery.io"
    )
    
    st.markdown("---")
    st.caption("Made with ❤️ for memecoin traders")
    st.caption("الحمد لله")

# Main area
st.markdown("---")

col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    st.markdown(f"""
    ### 📍 Selected Time Range
    **Date:** {selected_date.strftime('%Y-%m-%d')}  
    **From:** {start_datetime.strftime('%H:%M:%S')} UTC  
    **To:** {end_datetime.strftime('%H:%M:%S')} UTC  
    **Tracking Duration:** {tracking_hours} hours per token
    """)
    
    # The magic button
    if st.button("🔥 RUN TRACKER", use_container_width=True, type="primary"):
        
        if not bitquery_token:
            st.error("❌ Please enter your Bitquery API token in the sidebar")
            st.info("👉 Get your free token at: https://graphql.bitquery.io")
        else:
            # Progress containers
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # Initialize clients
                status_text.text("🔧 Initializing Bitquery client...")
                bitquery = BitqueryClient(bitquery_token)
                processor = TokenProcessor(bitquery)
                
                # Progress callback
                def update_progress(current, total, message):
                    progress_bar.progress(current / total)
                    status_text.text(f"⏳ {message}")
                
                # Process tokens
                status_text.text("🔍 Fetching token launches from Bitquery...")
                
                successful, failed, summary = processor.process_tokens_for_timerange(
                    start_datetime,
                    end_datetime,
                    progress_callback=update_progress
                )
                
                # Clear progress indicators
                progress_bar.empty()
                status_text.empty()
                
                # Check if any tokens were found
                if summary.get('total_tokens_analyzed', 0) == 0:
                    st.warning("⚠️ No tokens found in this time range!")
                    
                    if 'warning' in summary:
                        st.info(summary['warning'])
                    
                    st.markdown("""
                    ### 🔧 Troubleshooting:
                    
                    1. **Try a different date:**
                       - Bitquery free tier may have 24-48h delay
                       - Try dates from **2-3 days ago**
                    
                    2. **Check your time range:**
                       - Use "Prime Time (14:00-22:00 UTC)" preset
                       - Most tokens launch during these hours
                    
                    3. **Verify Bitquery token:**
                       - Make sure your API token is valid
                       - Test it at https://graphql.bitquery.io/ide
                    
                    4. **Check Bitquery status:**
                       - API might be temporarily down
                       - Try again in 5-10 minutes
                    """)
                    st.stop()
                
                # Generate date label
                date_label = selected_date.strftime(config.DATE_FORMAT)
                
                # Save to files
                status_text.text("💾 Saving JSON files...")
                summary_file, successful_file, failed_file = processor.save_to_json_files(
                    successful,
                    failed,
                    summary,
                    date_label
                )
                
                st.success("✅ Processing complete! الحمد لله")
                
                # Display summary
                st.markdown("---")
                st.subheader("📊 Summary Report")
                
                # Summary metrics
                col_metric1, col_metric2, col_metric3 = st.columns(3)
                
                with col_metric1:
                    st.metric(
                        "Total Tokens Analyzed",
                        summary['total_tokens_analyzed']
                    )
                
                with col_metric2:
                    success_rate = (summary['successful_tokens']['total'] / max(summary['total_tokens_analyzed'], 1) * 100)
                    st.metric(
                        "✅ Successful",
                        summary['successful_tokens']['total'],
                        delta=f"{success_rate:.1f}% success rate"
                    )
                
                with col_metric3:
                    failure_rate = (summary['failed_tokens']['total'] / max(summary['total_tokens_analyzed'], 1) * 100)
                    st.metric(
                        "❌ Failed",
                        summary['failed_tokens']['total'],
                        delta=f"{failure_rate:.1f}% failure rate"
                    )
                
                # Detailed breakdown
                st.markdown("---")
                col_detail1, col_detail2 = st.columns(2)
                
                with col_detail1:
                    st.markdown("#### ✅ Successful Breakdown")
                    # Get dynamic keys from summary
                    breakdown = summary['successful_tokens']['breakdown']
                    roi_keys = list(breakdown.keys())
                    st.markdown(f"""
                    **📈 ROI Distribution:**
                    - **{roi_keys[0]}:** {breakdown[roi_keys[0]]} tokens
                    - **{roi_keys[1]}:** {breakdown[roi_keys[1]]} tokens
                    """)
                
                with col_detail2:
                    st.markdown("#### ❌ Failed Breakdown")
                    st.markdown(f"""
                    **💥 Failure Types:**
                    - **Pump & Dump:** {summary['failed_tokens']['breakdown']['pump_and_dump']} tokens
                    - **Rug Pull:** {summary['failed_tokens']['breakdown']['rug_pull']} tokens
                    """)
                
                # Download section
                st.markdown("---")
                st.subheader("📥 Download JSON Files")
                
                col_dl1, col_dl2, col_dl3 = st.columns(3)
                
                with col_dl1:
                    st.markdown("##### 📊 Summary")
                    with open(summary_file, 'r') as f:
                        st.download_button(
                            "📥 Download Summary",
                            f.read(),
                            file_name=f"summary_{date_label}.json",
                            mime="application/json",
                            use_container_width=True
                        )
                
                with col_dl2:
                    st.markdown("##### ✅ Successful")
                    if successful:
                        with open(successful_file, 'r') as f:
                            st.download_button(
                                "📥 Download Successful",
                                f.read(),
                                file_name=f"successful_tokens_{date_label}.json",
                                mime="application/json",
                                use_container_width=True
                            )
                        st.caption(f"{len(successful)} tokens")
                    else:
                        st.info("No successful tokens")
                
                with col_dl3:
                    st.markdown("##### ❌ Failed")
                    if failed:
                        with open(failed_file, 'r') as f:
                            st.download_button(
                                "📥 Download Failed",
                                f.read(),
                                file_name=f"failed_tokens_{date_label}.json",
                                mime="application/json",
                                use_container_width=True
                            )
                        st.caption(f"{len(failed)} tokens")
                    else:
                        st.info("No failed tokens")
                
                # Preview
                st.markdown("---")
                st.subheader("👀 Preview (First 3 Tokens)")
                
                col_prev1, col_prev2 = st.columns(2)
                
                with col_prev1:
                    st.markdown("#### ✅ Successful")
                    if successful:
                        st.json(successful[:3])
                    else:
                        st.info("No tokens to preview")
                
                with col_prev2:
                    st.markdown("#### ❌ Failed")
                    if failed:
                        st.json(failed[:3])
                    else:
                        st.info("No tokens to preview")
                
            except Exception as e:
                progress_bar.empty()
                status_text.empty()
                
                st.error(f"❌ Error: {str(e)}")
                st.error("Full error details:")
                st.code(str(e))

# Footer
st.markdown("---")
st.caption("🚀 Solana Memecoin Tracker | 🤲 الحمد لله رب العالمين")

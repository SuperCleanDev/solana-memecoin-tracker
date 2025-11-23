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
    .metric-card {
        background-color: #262730;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.title("🚀 Solana Memecoin Tracker")
st.markdown("**Track Pump.fun launches with accurate 24-hour on-chain data**")
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
        value=datetime.now() - timedelta(days=1),
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
    
    # Show criteria
    st.subheader("✅ Success Criteria")
    st.markdown(f"""
    - Peak MC ≥ **${config.SUCCESSFUL_TOKEN_CONFIG['min_peak_mc']:,}**
    - ROI ≥ **{config.SUCCESSFUL_TOKEN_CONFIG['min_roi_multiplier']}x** from $25K
    - Entry window: Launch to $25K MC
    - Tracking: **24 hours** from launch
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
    **Tracking Duration:** 24 hours per token
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
                
                # Clear progress indicators
                progress_bar.empty()
                status_text.empty()
                
                st.success("✅ Processing complete! الحمد لله")
                
                # Display summary
                st.markdown("---")
                st.subheader("📊 Summary Report")
                
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

# Summary metrics
col_metric1, col_metric2, col_metric3 = st.columns(3)

with col_metric1:
    st.metric(
        "Total Tokens Analyzed",
        summary['total_tokens_analyzed'],
        delta=None
    )
                
                with col_metric2:
                    st.metric(
                        "✅ Successful",
                        summary['successful_tokens']['total'],
                        delta=f"{(summary['successful_tokens']['total'] / max(summary['total_tokens_analyzed'], 1) * 100):.1f}% success rate"
                    )
                
                with col_metric3:
                    st.metric(
                        "❌ Failed",
                        summary['failed_tokens']['total'],
                        delta=f"{(summary['failed_tokens']['total'] / max(summary['total_tokens_analyzed'], 1) * 100):.1f}% failure rate"
                    )
                
                # Detailed breakdown
                st.markdown("---")
                col_detail1, col_detail2 = st.columns(2)
                
                with col_detail1:
                    st.markdown("#### ✅ Successful Breakdown")
                    st.markdown(f"""
                    <div class="metric-card">
                    <h3>📈 ROI Distribution</h3>
                    <ul>
                        <li><strong>50x-79x:</strong> {summary['successful_tokens']['breakdown']['50x_to_79x']} tokens</li>
                        <li><strong>80x+:</strong> {summary['successful_tokens']['breakdown']['80x_plus']} tokens</li>
                    </ul>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col_detail2:
                    st.markdown("#### ❌ Failed Breakdown")
                    st.markdown(f"""
                    <div class="metric-card">
                    <h3>💥 Failure Types</h3>
                    <ul>
                        <li><strong>Pump & Dump:</strong> {summary['failed_tokens']['breakdown']['pump_and_dump']} tokens</li>
                        <li><strong>Rug Pull:</strong> {summary['failed_tokens']['breakdown']['rug_pull']} tokens</li>
                    </ul>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Download section
                st.markdown("---")
                st.subheader("📥 Download JSON Files")
                st.markdown("*Download these files for use in your Dune Analytics queries*")
                
                col_dl1, col_dl2, col_dl3 = st.columns(3)
                
                with col_dl1:
                    st.markdown("##### 📊 Summary")
                    with open(summary_file, 'r') as f:
                        summary_json = f.read()
                        st.download_button(
                            "📥 Download Summary JSON",
                            summary_json,
                            file_name=f"summary_{date_label}.json",
                            mime="application/json",
                            use_container_width=True
                        )
                    st.caption(f"Contains full statistics")
                
                with col_dl2:
                    st.markdown("##### ✅ Successful")
                    if successful:
                        with open(successful_file, 'r') as f:
                            successful_json = f.read()
                            st.download_button(
                                "📥 Download Successful JSON",
                                successful_json,
                                file_name=f"successful_tokens_{date_label}.json",
                                mime="application/json",
                                use_container_width=True
                            )
                        st.caption(f"{len(successful)} tokens")
                    else:
                        st.info("No successful tokens found")
                
                with col_dl3:
                    st.markdown("##### ❌ Failed")
                    if failed:
                        with open(failed_file, 'r') as f:
                            failed_json = f.read()
                            st.download_button(
                                "📥 Download Failed JSON",
                                failed_json,
                                file_name=f"failed_tokens_{date_label}.json",
                                mime="application/json",
                                use_container_width=True
                            )
                        st.caption(f"{len(failed)} tokens")
                    else:
                        st.info("No failed tokens found")
                
                # Preview section
                st.markdown("---")
                st.subheader("👀 Preview (First 3 Tokens)")
                
                col_prev1, col_prev2 = st.columns(2)
                
                with col_prev1:
                    st.markdown("#### ✅ Successful Tokens")
                    if successful:
                        st.json(successful[:3])
                    else:
                        st.info("No successful tokens to preview")
                
                with col_prev2:
                    st.markdown("#### ❌ Failed Tokens")
                    if failed:
                        st.json(failed[:3])
                    else:
                        st.info("No failed tokens to preview")
                
                # Instructions for Dune
                st.markdown("---")
                st.subheader("📖 How to Use with Dune Analytics")
                
                with st.expander("Click to see instructions"):
                    st.markdown("""
                    ### Step-by-Step Guide:
                    
                    1. **Download the JSON files** using the buttons above
                    
                    2. **Open your Dune query editor**
                    
                    3. **For Successful Tokens:**
                       - Open `successful_tokens_YYYY-MM-DD.json`
                       - Copy the entire JSON array
                       - In Dune, create a parameter named `successful_tokens_json`
                       - Paste the JSON array as the value
                    
                    4. **For Failed Tokens:**
                       - Open `failed_tokens_YYYY-MM-DD.json`
                       - Copy the entire JSON array
                       - In Dune, create a parameter named `failed_tokens_json`
                       - Paste the JSON array as the value
                    
                    5. **Run your Dune query** with these parameters
                    
                    ### Example Dune Query:
```sql
                    -- Parse successful tokens JSON
                    WITH successful_tokens AS (
                        SELECT
                            json_value(value, '$.token_address') as token_address,
                            json_value(value, '$.launch_time') as launch_time,
                            json_value(value, '$.entry_start') as entry_start,
                            json_value(value, '$.entry_end') as entry_end
                        FROM json_array_elements('{{successful_tokens_json}}')
                    )
                    
                    -- Your analysis here
                    SELECT * FROM successful_tokens;
```
                    
                    **Need Help?** Check the summary file for detailed statistics.
                    """)
                
            except Exception as e:
                progress_bar.empty()
                status_text.empty()
                
                st.error(f"❌ Error: {str(e)}")
                
                with st.expander("🔧 Troubleshooting"):
                    st.markdown("""
                    ### Common Issues:
                    
                    1. **Bitquery API Error (401):**
                       - Your API token is invalid
                       - Get a new token from https://graphql.bitquery.io
                    
                    2. **Bitquery API Error (429):**
                       - Rate limit exceeded
                       - Wait a few minutes before trying again
                       - Use a smaller time range
                    
                    3. **No tokens found:**
                       - Try a different date
                       - Bitquery free tier may have 24-48h delay for historical data
                       - Try dates from 2-3 days ago
                    
                    4. **Timeout Error:**
                       - Too many tokens to process
                       - Use a smaller time window (6-8 hours instead of 24)
                       - Try Prime Time preset (14:00-22:00 UTC)
                    
                    5. **App is slow:**
                       - 24-hour tracking takes time
                       - Expected: 10-15 minutes for full run
                       - Be patient, grab some tea ☕
                    
                    **Still stuck?** Check Bitquery status or try again later.
                    """)

# Footer
st.markdown("---")
col_foot1, col_foot2, col_foot3 = st.columns(3)

with col_foot1:
    st.caption("🚀 **Solana Memecoin Tracker**")
    st.caption("Version 1.0 - Phase 1")

with col_foot2:
    st.caption("📊 **Data Source**")
    st.caption("Bitquery GraphQL API")

with col_foot3:
    st.caption("🤲 **Made with**")
    st.caption("الحمد لله رب العالمين")

st.markdown("---")
st.info("""
💡 **Pro Tips:**
- Run during low-traffic hours for faster processing
- Prime Time (14:00-22:00 UTC) has the most successful tokens
- Collect data daily for 30 days before ML training
- Keep your Bitquery token safe - don't share it
""")

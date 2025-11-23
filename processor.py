"""
بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ
Token Processor - Categorizes and formats tokens according to your criteria
"""

from datetime import datetime, timedelta
import json
import os
import config

class TokenProcessor:
    
    def __init__(self, bitquery_client):
        self.bitquery = bitquery_client
    
    def process_tokens_for_timerange(self, start_datetime, end_datetime, progress_callback=None):
        """
        Main processing function
        Gets all tokens from timerange and categorizes them
        """
        print(f"📅 Processing tokens from {start_datetime} to {end_datetime}...")
        
        # Step 1: Get all launches in UI window
        tokens = self.bitquery.get_tokens_launched_in_timerange(start_datetime, end_datetime)
        print(f"✅ Found {len(tokens)} token launches")
        
        if not tokens:
            print("⚠️ No tokens found in this time range")
            return [], [], {}
        
        # Limit processing if too many tokens
        if len(tokens) > config.MAX_TOKENS_TO_PROCESS:
            print(f"⚠️ Found {len(tokens)} tokens, limiting to {config.MAX_TOKENS_TO_PROCESS}")
            tokens = tokens[:config.MAX_TOKENS_TO_PROCESS]
        
        # Step 2: Track each token for 24 hours from launch
        enriched_tokens = []
        total = len(tokens)
        
        for i, token in enumerate(tokens, 1):
            # Progress update
            if progress_callback:
                progress_callback(i, total, f"Processing token {i}/{total}")
            
            # Calculate 24-hour tracking window from launch
            launch_dt = datetime.fromisoformat(token['launch_time'].replace('Z', '+00:00'))
            track_end_dt = launch_dt + timedelta(hours=config.ANALYSIS_WINDOW['tracking_duration_hours'])
            
            # Get price history for this token's 24-hour window
            trades = self.bitquery.get_token_price_history(
                token['token_address'],
                launch_dt,
                track_end_dt
            )
            
            if trades:
                enriched = self._enrich_token_data(token, trades)
                if enriched:
                    enriched_tokens.append(enriched)
        
        print(f"\n✅ Successfully enriched {len(enriched_tokens)} tokens")
        
        # Step 3: Categorize
        successful, failed = self._categorize_tokens(enriched_tokens)
        
        # Step 4: Generate summary statistics
        summary = self._generate_summary(start_datetime, end_datetime, enriched_tokens, successful, failed)
        
        print(f"\n📊 Categorization complete:")
        print(f"   ✅ Successful: {len(successful)}")
        print(f"   ❌ Failed: {len(failed)}")
        
        return successful, failed, summary
    
    def _enrich_token_data(self, token, trades):
        """Calculate all metrics from trade data"""
        if not trades:
            return None
        
        try:
            supply = self.bitquery.get_token_supply(token['token_address'])
            
            prices = [float(trade['Trade']['PriceInUSD']) for trade in trades if trade['Trade'].get('PriceInUSD')]
            
            if not prices:
                return None
            
            # Basic metrics
            launch_price = prices[0]
            peak_price = max(prices)
            final_price = prices[-1]
            
            launch_mc = self.bitquery.calculate_mc_from_price_and_supply(launch_price, supply)
            peak_mc = self.bitquery.calculate_mc_from_price_and_supply(peak_price, supply)
            final_mc = self.bitquery.calculate_mc_from_price_and_supply(final_price, supply)
            
            # Find peak time
            peak_trade = max(trades, key=lambda t: float(t['Trade'].get('PriceInUSD', 0)))
            peak_time = peak_trade['Block']['Time']
            
            # Calculate entry_end (when MC hits $25K or fallback)
            entry_end_time, entry_end_mc = self._calculate_entry_end(token, trades, supply)
            
            # Calculate liquidity
            liquidities = [float(trade['Trade']['Side']['AmountInUSD']) for trade in trades 
                          if trade['Trade']['Side'].get('AmountInUSD')]
            avg_liquidity = sum(liquidities) / len(liquidities) if liquidities else 0
            final_liquidity = liquidities[-1] if liquidities else 0
            
            # Tank percentage
            tank_percentage = ((peak_mc - final_mc) / peak_mc * 100) if peak_mc > 0 else 0
            
            # ROI from entry_end
            roi_from_entry_end = (peak_mc / entry_end_mc) if entry_end_mc > 0 else 0
            
            return {
                **token,
                'supply': supply,
                'launch_price': launch_price,
                'launch_mc': launch_mc,
                'peak_time': peak_time,
                'peak_price': peak_price,
                'peak_mc': peak_mc,
                'final_price': final_price,
                'final_mc': final_mc,
                'entry_end_time': entry_end_time,
                'entry_end_mc': entry_end_mc,
                'tank_percentage': tank_percentage,
                'roi_from_entry_end': roi_from_entry_end,
                'avg_liquidity': avg_liquidity,
                'final_liquidity': final_liquidity
            }
            
        except Exception as e:
            print(f"❌ Error enriching {token['token_address'][:8]}: {e}")
            return None
    
    def _calculate_entry_end(self, token, trades, supply):
        """
        Calculate entry_end time and MC
        Logic: When MC hits $25K, or launch + 5 mins if already above $25K
        """
        threshold = config.SUCCESSFUL_TOKEN_CONFIG['entry_end_mc_threshold']
        fallback_mins = config.SUCCESSFUL_TOKEN_CONFIG['entry_end_fallback_minutes']
        
        launch_dt = datetime.fromisoformat(token['launch_time'].replace('Z', '+00:00'))
        
        # Check each trade to find when MC hit $25K
        for trade in trades:
            price = float(trade['Trade'].get('PriceInUSD', 0))
            mc = self.bitquery.calculate_mc_from_price_and_supply(price, supply)
            trade_time = trade['Block']['Time']
            
            if mc >= threshold:
                return trade_time, mc
        
        # Fallback: launch + 5 minutes
        fallback_time = (launch_dt + timedelta(minutes=fallback_mins)).strftime(config.DATETIME_FORMAT)
        
        # Use launch_mc as fallback
        launch_price = float(trades[0]['Trade']['PriceInUSD'])
        fallback_mc = self.bitquery.calculate_mc_from_price_and_supply(launch_price, supply)
        
        return fallback_time, fallback_mc
    
    def _categorize_tokens(self, enriched_tokens):
        """Apply success/failure criteria"""
        successful = []
        failed = []
        
        for token in enriched_tokens:
            if self._is_successful(token):
                successful.append(self._format_successful_token(token))
            elif self._is_failed(token):
                failed.append(self._format_failed_token(token))
        
        # Limit to configured maxes
        successful = successful[:config.MAX_SUCCESSFUL_TOKENS]
        failed = failed[:config.MAX_FAILED_TOKENS]
        
        return successful, failed
    
    def _is_successful(self, token):
        """Check if token meets success criteria"""
        cfg = config.SUCCESSFUL_TOKEN_CONFIG
        
        return (
            token['roi_from_entry_end'] >= cfg['min_roi_multiplier'] and
            token['peak_mc'] >= cfg['min_peak_mc']
        )
    
    def _is_failed(self, token):
        """Check if token meets failure criteria"""
        cfg = config.FAILED_TOKEN_CONFIG
        
        # Type 1: Pump & Dump
        is_pump_dump = (
            cfg['pump_and_dump']['enabled'] and
            token['peak_mc'] >= cfg['pump_and_dump']['min_initial_mc'] and
            token['peak_mc'] <= cfg['pump_and_dump']['max_peak_mc'] and
            token['tank_percentage'] >= cfg['pump_and_dump']['min_tank_percentage']
        )
        
        # Type 2: Rug Pull
        is_rug = (
            cfg['rug_pull']['enabled'] and
            token['peak_mc'] >= cfg['rug_pull']['min_initial_mc'] and
            token['final_liquidity'] <= cfg['rug_pull']['max_final_liquidity']
        )
        
        return is_pump_dump or is_rug
    
    def _format_successful_token(self, token):
        """Format to EXACT JSON structure specified"""
        entry_start = token['launch_time']
        entry_end = token['entry_end_time']
        
        # Calculate holder_snapshot (peak_time - 10 minutes)
        peak_dt = datetime.fromisoformat(token['peak_time'].replace('Z', '+00:00'))
        snapshot_dt = peak_dt - timedelta(minutes=config.SUCCESSFUL_TOKEN_CONFIG['holder_snapshot_before_peak_minutes'])
        holder_snapshot = snapshot_dt.strftime(config.DATETIME_FORMAT)
        
        return {
            "token_address": token['token_address'],
            "launch_time": entry_start,
            "launch_mc": int(token['launch_mc']),
            "peak_time": token['peak_time'],
            "peak_mc": int(token['peak_mc']),
            "total_supply": token['supply'],
            "entry_start": entry_start,
            "entry_end": entry_end,
            "holder_snapshot": holder_snapshot
        }
    
    def _format_failed_token(self, token):
        """Format failed tokens (simplified)"""
        launch_dt = datetime.fromisoformat(token['launch_time'].replace('Z', '+00:00'))
        entry_end_dt = launch_dt + timedelta(minutes=config.FAILED_TOKEN_CONFIG['entry_window_minutes'])
        
        return {
            "token_address": token['token_address'],
            "entry_start": token['launch_time'],
            "entry_end": entry_end_dt.strftime(config.DATETIME_FORMAT)
        }
    
        def _generate_summary(self, start_dt, end_dt, enriched, successful, failed):
    """Generate summary statistics"""
    
    # Handle case when no tokens were enriched
    if not enriched:
        return {
            "date": start_dt.strftime(config.DATE_FORMAT),
            "analysis_window": f"{start_dt.strftime('%H:%M')} to {end_dt.strftime('%H:%M')} UTC",
            "tracking_duration_hours": config.ANALYSIS_WINDOW['tracking_duration_hours'],
            "total_tokens_analyzed": 0,
            "successful_tokens": {
                "total": 0,
                "breakdown": {
                    "50x_to_79x": 0,
                    "80x_plus": 0
                }
            },
            "failed_tokens": {
                "total": 0,
                "breakdown": {
                    "pump_and_dump": 0,
                    "rug_pull": 0
                }
            },
            "warning": "No tokens were found or successfully enriched. Try a different date or time range."
        }
    
    # ROI breakdown for successful tokens
    roi_50_79 = len([t for t in enriched if 50 <= t.get('roi_from_entry_end', 0) < 80])
    roi_80_plus = len([t for t in enriched if t.get('roi_from_entry_end', 0) >= 80])
    
    # Failure type breakdown
    pump_dump_count = 0
    rug_pull_count = 0
    
    for t in enriched:
        if self._is_pump_dump(t):
            pump_dump_count += 1
        if self._is_rug_pull(t):
            rug_pull_count += 1
    
    return {
        "date": start_dt.strftime(config.DATE_FORMAT),
        "analysis_window": f"{start_dt.strftime('%H:%M')} to {end_dt.strftime('%H:%M')} UTC",
        "tracking_duration_hours": config.ANALYSIS_WINDOW['tracking_duration_hours'],
        "total_tokens_analyzed": len(enriched),
        "successful_tokens": {
            "total": len(successful),
            "breakdown": {
                "50x_to_79x": roi_50_79,
                "80x_plus": roi_80_plus
            }
        },
        "failed_tokens": {
            "total": len(failed),
            "breakdown": {
                "pump_and_dump": pump_dump_count,
                "rug_pull": rug_pull_count
            }
        }
    }
    
    def _is_pump_dump(self, token):
        """Check if token is pump & dump"""
        cfg = config.FAILED_TOKEN_CONFIG['pump_and_dump']
        return (
            cfg['enabled'] and
            token['peak_mc'] >= cfg['min_initial_mc'] and
            token['peak_mc'] <= cfg['max_peak_mc'] and
            token['tank_percentage'] >= cfg['min_tank_percentage']
        )
    
    def _is_rug_pull(self, token):
        """Check if token is rug pull"""
        cfg = config.FAILED_TOKEN_CONFIG['rug_pull']
        return (
            cfg['enabled'] and
            token['peak_mc'] >= cfg['min_initial_mc'] and
            token['final_liquidity'] <= cfg['max_final_liquidity']
        )
    
    def save_to_json_files(self, successful_tokens, failed_tokens, summary, date_label):
        """Save to separate JSON files"""
        os.makedirs(config.OUTPUT_DIR, exist_ok=True)
        date_dir = os.path.join(config.OUTPUT_DIR, date_label)
        os.makedirs(date_dir, exist_ok=True)
        
        # Save summary
        summary_file = os.path.join(date_dir, f"summary_{date_label}.json")
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        # Save successful tokens
        successful_file = os.path.join(date_dir, f"successful_tokens_{date_label}.json")
        with open(successful_file, 'w') as f:
            json.dump(successful_tokens, f, indent=2)
        
        # Save failed tokens
        failed_file = os.path.join(date_dir, f"failed_tokens_{date_label}.json")
        with open(failed_file, 'w') as f:
            json.dump(failed_tokens, f, indent=2)
        
        print(f"\n💾 Files saved:")
        print(f"   📊 {summary_file}")
        print(f"   ✅ {successful_file}")
        print(f"   ❌ {failed_file}")
        
        return summary_file, successful_file, failed_file

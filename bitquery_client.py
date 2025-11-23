"""
بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ
Bitquery Client - Fetches accurate historical Pump.fun data
"""

import requests
from datetime import datetime, timedelta
import config

class BitqueryClient:
    
    def __init__(self, api_token):
        self.api_token = api_token
        self.api_url = config.BITQUERY_API_URL
        self.headers = {
            "X-API-KEY": api_token,
            "Content-Type": "application/json"
        }
    
    def get_tokens_launched_in_timerange(self, start_datetime, end_datetime):
        """
        Get all Pump.fun tokens launched in a specific time range
        Returns list of tokens with launch time, CA, supply
        """
        start_iso = start_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_iso = end_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        query = """
        {
          Solana(dataset: realtime) {
            Instructions(
              where: {
                Instruction: {
                  Program: {
                    Method: {in: ["create", "create_v2"]}
                    Name: {is: "pump"}
                  }
                }
                Block: {
                  Time: {since: "%s", till: "%s"}
                }
              }
              limit: {count: 1000}
              orderBy: {ascending: Block_Time}
            ) {
              Block {
                Time
              }
              Instruction {
                Accounts {
                  Address
                }
                Program {
                  Arguments {
                    Name
                    Value {
                      ... on Solana_ABI_Integer_Value_Arg {
                        integer
                      }
                      ... on Solana_ABI_String_Value_Arg {
                        string
                      }
                      ... on Solana_ABI_BigInt_Value_Arg {
                        bigInteger
                      }
                    }
                  }
                }
              }
              Transaction {
                Signature
              }
            }
          }
        }
        """ % (start_iso, end_iso)
        
        try:
            response = requests.post(
                self.api_url,
                json={"query": query},
                headers=self.headers,
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_token_launches(data)
            else:
                print(f"❌ Bitquery API error: {response.status_code}")
                print(f"Response: {response.text}")
                return []
                
        except Exception as e:
            print(f"❌ Error fetching tokens: {e}")
            return []
    
    def get_token_price_history(self, token_address, start_datetime, end_datetime):
        """
        Get price history for a token in a specific time range
        Returns list of trades with prices and liquidity
        """
        start_iso = start_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_iso = end_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        query = """
        {
          Solana(dataset: realtime) {
            DEXTradeByTokens(
              where: {
                Trade: {
                  Currency: {MintAddress: {is: "%s"}}
                  PriceInUSD: {gt: 0}
                }
                Block: {
                  Time: {since: "%s", till: "%s"}
                }
              }
              orderBy: {ascending: Block_Time}
              limit: {count: 1000}
            ) {
              Block {
                Time
              }
              Trade {
                Price
                PriceInUSD
                AmountInUSD
                Currency {
                  MintAddress
                  Symbol
                }
                Side {
                  Currency {
                    Symbol
                  }
                  AmountInUSD
                }
              }
            }
          }
        }
        """ % (token_address, start_iso, end_iso)
        
        try:
            response = requests.post(
                self.api_url,
                json={"query": query},
                headers=self.headers,
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                trades = data.get('data', {}).get('Solana', {}).get('DEXTradeByTokens', [])
                return trades
            else:
                return []
                
        except Exception as e:
            print(f"❌ Error fetching price history for {token_address[:8]}: {e}")
            return []
    
    def get_token_supply(self, token_address):
        """
        Get total supply for a token from Solscan
        """
        try:
            response = requests.get(
                f"{config.SOLSCAN_API_URL}/token/meta",
                params={"token": token_address},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                supply_str = data.get('supply', '0')
                supply = int(float(supply_str))
                return supply if supply > 0 else config.PUMPFUN_DEFAULT_SUPPLY
        except:
            pass
        
        return config.PUMPFUN_DEFAULT_SUPPLY
    
    def calculate_mc_from_price_and_supply(self, price_usd, supply):
        """Calculate market cap: Price * Supply"""
        if price_usd is None or supply is None:
            return 0
        return float(price_usd) * int(supply)
    
    def _parse_token_launches(self, bitquery_response):
        """Parse Bitquery response to extract token details"""
        tokens = []
        instructions = bitquery_response.get('data', {}).get('Solana', {}).get('Instructions', [])
        
        for instr in instructions:
            try:
                accounts = instr.get('Instruction', {}).get('Accounts', [])
                
                # For pump.fun, token mint is at index 4
                token_address = None
                if len(accounts) > 4:
                    token_address = accounts[4].get('Address')
                
                if not token_address:
                    continue
                
                launch_time = instr.get('Block', {}).get('Time')
                
                tokens.append({
                    'token_address': token_address,
                    'launch_time': launch_time,
                    'signature': instr.get('Transaction', {}).get('Signature')
                })
                
            except Exception as e:
                continue
        
        return tokens

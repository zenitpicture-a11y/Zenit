import os
import random
import time
import requests
from datetime import datetime
from eth_account import Account
from tronapi import Tron
from bip_utils import Bip39SeedGenerator, Bip44, Bip44Coins

# Configuration
ENABLE_TOKENS = False
SCAN_COINS = ["ETH", "BSC", "TRX"]
MIN_BALANCE_ETH = 0.001
MIN_BALANCE_TRX = 10

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

WORDLIST_URL = "https://raw.githubusercontent.com/wordlists/bip39/master/english.txt"

def get_wordlist():
    try:
        response = requests.get(WORDLIST_URL)
        return response.text.strip().split('\n')
    except Exception as e:
        print(f"[ERR] Fetch wordlist: {e}")
        # Fallback wordlist (first 50 words of BIP39)
        return [
            "abandon", "ability", "able", "about", "above", "absent", "absorb", "abstract", "absurd", "abuse",
            "access", "accident", "account", "accuse", "achieve", "acid", "acoustic", "acquire", "across", "act",
            "action", "actor", "actress", "actual", "adapt", "add", "addict", "address", "adjust", "admit"
        ] + ["age", "aid", "aim", "air", "airport", "aisle", "alarm", "album", "alcohol", "alert"]

def generate_mnemonic():
    wordlist = get_wordlist()
    while True:
        mnemonic = ' '.join(random.sample(wordlist, 12))
        # Simple check: just ensure it's 12 words for now to keep it fast
        if len(mnemonic.split()) == 12:
            return mnemonic

def derive_eth_address(mnemonic):
    account = Account.from_mnemonic(mnemonic, account_path="m/44'/60'/0'/0/0")
    return account.address

def derive_tron_address(mnemonic):
    seed = Bip39SeedGenerator(mnemonic).Generate()
    bip44 = Bip44.FromSeed(seed, Bip44Coins.TRON)
    priv_key_bytes = bip44.Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(0).PrivateKey().Raw().ToBytes()
    return TronPrivateKey(priv_key_bytes).public_key.to_base58check_address()

def check_eth_balance(address):
    url = f"https://eth.llamarpc.com" # Free RPC
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_getBalance",
        "params": [address, "latest"],
        "id": 1
    }
    try:
        res = requests.post(url, json=payload).json()
        if 'result' in res:
            wei = int(res['result'], 16)
            return wei / 10**18
    except:
        pass
    return 0

def check_tron_balance(address):
    url = "https://api.trongrid.io/v1/accounts"
    params = {"address": address}
    try:
        res = requests.get(url, params=params).json()
        if 'balance' in res:
            return res['balance'] / 10**6
    except:
        pass
    return 0

def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message})

def main():
    print(f"--- Scan started at {datetime.now()} ---")
    found_wallets = []
    
    # Generate 10 wallets per run to avoid rate limits on free GitHub Actions
    for i in range(10):
        mnem = generate_mnemonic()
        
        # ETH Check
        eth_addr = derive_eth_address(mnem)
        bal_eth = check_eth_balance(eth_addr)
        
        # TRX Check
        tron_addr = derive_tron_address(mnem)
        bal_trx = check_tron_balance(tron_addr)
        
        result_msg = ""
        if bal_eth > MIN_BALANCE_ETH:
            result_msg += f"🟢 ETH Found!\nAddress: `{eth_addr}`\nBalance: `{bal_eth:.6f} ETH`\n\n"
            
        if bal_trx > MIN_BALANCE_TRX:
            result_msg += f"🟣 TRX Found!\nAddress: `{tron_addr}`\nBalance: `{bal_trx:.2f} TRX`\n\n"
            
        if result_msg:
            found_wallets.append(result_msg)
            print(result_msg)
            
        # Small delay to be polite to RPCs
        time.sleep(1)

    if found_wallets:
        full_report = "🔥 **Hot Wallets Found!** 🔥\n\n" + "\n".join(found_wallets)
        send_telegram(full_report)
        print("Report sent to Telegram!")
    else:
        print("No hot wallets found in this batch.")

if __name__ == "__main__":
    main()

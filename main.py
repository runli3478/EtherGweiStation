import os
import requests
from flask import Flask
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, CallbackContext, JobQueue
from web3 import Web3

app = Flask(__name__)

# Set up Telegram bot API
TELEGRAM_API_TOKEN = os.environ['BOT_TOKEN']
bot = Bot(token=TELEGRAM_API_TOKEN)

# Retrieve INFURA_PROJECT_ID, ARBISCAN_API_KEY, and OPTIMISM_API_KEY from the OS environment
INFURA_PROJECT_ID = os.environ['INFURA_PROJECT_ID']
ARBISCAN_API_KEY = os.environ['ARBISCAN_API_KEY']
OPTIMISM_API_KEY = os.environ['OPTIMISM_API_KEY']

# Initialize global variable for chat ID
user_chat_id = None

def get_eth_gas_price() -> int:
    try:
        url = f'https://mainnet.infura.io/v3/{INFURA_PROJECT_ID}'
        data = {
            "jsonrpc": "2.0",
            "method": "eth_gasPrice",
            "params": [],
            "id": 1
        }
        headers = {
            "Content-Type": "application/json"
        }
        response = requests.post(url, json=data, headers=headers)

        if response.status_code == 200:
            result = response.json()
            gas_price = int(result['result'], 16)
            gas_price_gwei = gas_price / 1e9
            return gas_price_gwei
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return -1
    except Exception as e:
        print(f"Error fetching gas price for Ethereum: {e}")
        return -1

def get_arbitrum_gas_price() -> int:
    try:
        url = "https://api.arbiscan.io/api"
        params = {
            "module": "proxy",
            "action": "eth_gasPrice",
            "apikey": ARBISCAN_API_KEY
        }
        response = requests.get(url, params=params)

        if response.status_code == 200:
            result = response.json()
            gas_price = int(result['result'], 16)
            gas_price_gwei = gas_price / 1e9
            return gas_price_gwei
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return -1
    except Exception as e:
        print(f"Error fetching gas price for Arbitrum: {e}")
        return -1

def get_optimism_gas_price() -> int:
    try:
        url = "https://api-optimistic.etherscan.io/api"
        params = {
            "module": "proxy",
            "action": "eth_gasPrice",
            "apikey": OPTIMISM_API_KEY
        }
        response = requests.get(url, params=params)

        if response.status_code == 200:
            result = response.json()
            gas_price = int(result['result'], 16)
            gas_price_gwei = gas_price / 1e9
            return gas_price_gwei
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return -1
    except Exception as e:
        print(f"Error fetching gas price for Optimism: {e}")
        return -1

def get_ethereum_price() -> float:
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            "ids": "ethereum",
            "vs_currencies": "usd"
        }
        response = requests.get(url, params=params)

        if response.status_code == 200:
            result = response.json()
            ethereum_price = result['ethereum']['usd']
            return ethereum_price
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return -1
    except Exception as e:
        print(f"Error fetching Ethereum price: {e}")
        return -1

def calculate_send_fee(gas_price_gwei: float, ethereum_price: float) -> float:
    gas_limit = 21000  # Standard gas limit for a simple send transaction
    send_gas_fee_eth = gas_price_gwei * gas_limit / 1e9
    send_fee_usd = send_gas_fee_eth * ethereum_price
    return send_fee_usd

def get_uniswap_v3_swap_fee(gas_price_gwei: float, ethereum_price: float) -> float:
    swap_gas_units = 152809  # Assuming a simple swap using Uniswap V3 requires 150000 gas units
    swap_gas_fee_eth = gas_price_gwei * swap_gas_units / 1e9
    swap_fee_usd = swap_gas_fee_eth * ethereum_price
    return swap_fee_usd

def get_swap_fee(arbitrum_gas_price: float, optimism_gas_price: float, ethereum_price: float) -> (float, float, float):
    # Calculate swap fee for mainnet (Uniswap V3)
    mainnet_gas_price_gwei = get_eth_gas_price()
    mainnet_swap_fee_usd = get_uniswap_v3_swap_fee(mainnet_gas_price_gwei, ethereum_price)

    # Calculate swap fee for Arbitrum
    arbitrum_swap_fee_usd = get_uniswap_v3_swap_fee(arbitrum_gas_price, ethereum_price)

    # Calculate swap fee for Optimism
    optimism_swap_fee_usd = get_uniswap_v3_swap_fee(optimism_gas_price, ethereum_price)

    return arbitrum_swap_fee_usd, optimism_swap_fee_usd, mainnet_swap_fee_usd

def send_gas_prices(update: Update, context: CallbackContext):
    eth_gas_price = get_eth_gas_price()
    arbitrum_gas_price = get_arbitrum_gas_price()
    optimism_gas_price = get_optimism_gas_price()
    ethereum_price = get_ethereum_price()

    if eth_gas_price != -1:
        update.message.reply_text(f"Current Gas Price (Ethereum⚫): {eth_gas_price:.2f} Gwei")
        update.message.reply_text(f"Send Fee (Ethereum): {calculate_send_fee(eth_gas_price, ethereum_price):.4f} USD")
        update.message.reply_text(f"Swap Fee (Ethereum - 🦄Uniswap V3): {get_uniswap_v3_swap_fee(eth_gas_price, ethereum_price):.4f} USD")
    else:
        update.message.reply_text("Error fetching Ethereum gas price. Please try again later.")

    if arbitrum_gas_price != -1:
        update.message.reply_text(f"Current Gas Price (Arbitrum🔵): {arbitrum_gas_price:.2f} Gwei")
        update.message.reply_text(f"Send Fee (Arbitrum): {calculate_send_fee(arbitrum_gas_price, ethereum_price):.4f} USD")
        update.message.reply_text(f"Swap Fee (Arbitrum - 🦄Uniswap V3): {get_uniswap_v3_swap_fee(arbitrum_gas_price, ethereum_price):.4f} USD")
    else:
        update.message.reply_text("Error fetching Arbitrum gas price. Please try again later.")

    if optimism_gas_price != -1:
        update.message.reply_text(f"Current Gas Price (Optimism🔴): {optimism_gas_price:.2f} Gwei")
        update.message.reply_text(f"Send Fee (Optimism): {calculate_send_fee(optimism_gas_price, ethereum_price):.4f} USD")
        update.message.reply_text(f"Swap Fee (Optimism - 🦄Uniswap V3): {get_uniswap_v3_swap_fee(optimism_gas_price, ethereum_price):.4f} USD")
    else:
        update.message.reply_text("Error fetching Optimism gas price. Please try again later.")

def update_gas_prices(context: CallbackContext):
    global user_chat_id
    if user_chat_id is not None:
        send_gas_prices(Update(0, message=None), context)  # Sending a dummy Update to reuse the send_gas_prices function

def start(update: Update, context: CallbackContext):
    global user_chat_id
    user_chat_id = update.effective_chat.id
    update.message.reply_text("Welcome to Ether Gwei Station🦇🔊!\n\nYou will now receive ⛽ gas prices ⟠ and swap fees updates every 1 hour. \n\nUse /gasprices to get the current gas prices and swap fees for Ethereum ⚫, Arbitrum 🔵, and Optimism 🔴.\n\nData provided by CoinGecko, Infura, Optimism Etherscan, Arbiscan.")

updater = Updater(bot=bot)
updater.dispatcher.add_handler(CommandHandler("start", start))
updater.dispatcher.add_handler(CommandHandler("gasprices", send_gas_prices))

# Start the JobQueue to update gas prices and swap fees every 1 hour
job_queue = updater.job_queue
job_queue.run_repeating(update_gas_prices, interval=3600, first=0, context=12345)

# Start the bot
updater.start_polling()

# Start Flask app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=81)


import discord
from discord.ext import commands
import json
import os

# Intents (required for certain features in newer discord.py versions)
intents = discord.Intents.all()
intents.messages = True

# Bot setup
bot = commands.Bot(command_prefix="!", intents=intents)

# Check if we already have a data file, else create one
if not os.path.exists("gold_data.json"):
    with open("gold_data.json", "w") as f:
        json.dump({}, f)

# Load data from file
def load_data():
    with open("gold_data.json", "r") as f:
        return json.load(f)

# Save data to file
def save_data(data):
    with open("gold_data.json", "w") as f:
        json.dump(data, f, indent=4)

# Event to notify when bot is ready
@bot.event
async def on_ready():
    print(f'{bot.user} is now running!')

# Conversion rates for D&D currency, the script reads all currency as copper
conversion_rates = {
    'cp': 1,      # 1 copper piece
    'sp': 10,     # 10 copper pieces = 1 silver piece
    'ep': 50,     # 50 copper pieces = 1 electrum piece
    'gp': 100,    # 100 copper pieces = 1 gold piece
    'pp': 1000    # 1000 copper pieces = 1 platinum piece
}

# Load data from file
def load_data():
    if not os.path.exists("gold_data.json"):
        return {}
    with open("gold_data.json", "r") as f:
        return json.load(f)

# Save data to file
def save_data(data):
    with open("gold_data.json", "w") as f:
        json.dump(data, f, indent=4)

# Convert all currency to a standard denomination (copper pieces)
def to_copper(amount, denomination):
    return amount * conversion_rates[denomination]

# Convert from copper to the highest currency denomination possible
def from_copper(copper_amount):
    pp = copper_amount // conversion_rates['pp']
    copper_amount %= conversion_rates['pp']
    
    gp = copper_amount // conversion_rates['gp']
    copper_amount %= conversion_rates['gp']
    
    ep = copper_amount // conversion_rates['ep']
    copper_amount %= conversion_rates['ep']
    
    sp = copper_amount // conversion_rates['sp']
    copper_amount %= conversion_rates['sp']
    
    cp = copper_amount
    return {'pp': pp, 'gp': gp, 'ep': ep, 'sp': sp, 'cp': cp}

# Helper function to format currency output
def format_currency(currency_dict):
    return ', '.join([f"{amount} {denom}" for denom, amount in currency_dict.items() if amount > 0])

# Command to check a player's balance
@bot.command()
async def balance(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author
    data = load_data()
    user_id = str(member.id)
    if user_id in data:
        user_balance = data[user_id]
        await ctx.send(f'{member.display_name} has {format_currency(user_balance)}.')
    else:
        await ctx.send(f'{member.display_name} has no recorded gold.')

# Command to add money
@bot.command()
async def add_money(ctx, member: discord.Member, amount: int, denomination: str):
    denomination = denomination.lower()
    if denomination not in conversion_rates:
        await ctx.send("Invalid denomination. Use cp, sp, ep, gp, or pp.")
        return
    data = load_data()
    user_id = str(member.id)
    copper_amount = to_copper(amount, denomination)

    if user_id in data:
        user_balance = data[user_id]
        user_balance_copper = sum([to_copper(user_balance[d], d) for d in user_balance])
        new_balance = user_balance_copper + copper_amount
        data[user_id] = from_copper(new_balance)
    else:
        data[user_id] = from_copper(copper_amount)

    save_data(data)
    await ctx.send(f'{amount} {denomination} added to {member.display_name}. New balance: {format_currency(data[user_id])}.')

# Command to subtract money
@bot.command()
async def subtract_money(ctx, member: discord.Member, amount: int, denomination: str):
    denomination = denomination.lower()
    if denomination not in conversion_rates:
        await ctx.send("Invalid denomination. Use cp, sp, ep, gp, or pp.")
        return
    data = load_data()
    user_id = str(member.id)
    copper_amount = to_copper(amount, denomination)

    if user_id in data:
        user_balance = data[user_id]
        user_balance_copper = sum([to_copper(user_balance[d], d) for d in user_balance])
        if copper_amount > user_balance_copper:
            await ctx.send(f"{member.display_name} doesn't have enough money.")
            return
        new_balance = user_balance_copper - copper_amount
        data[user_id] = from_copper(new_balance)
        save_data(data)
        await ctx.send(f'{amount} {denomination} subtracted from {member.display_name}. New balance: {format_currency(data[user_id])}.')
    else:
        await ctx.send(f'{member.display_name} has no recorded gold.')

# Command to split loot
@bot.command()
async def split(ctx, amount: int, denomination: str, *members: discord.Member):
    if not members:
        await ctx.send("You need to specify at least one member to split the loot with.")
        return
    denomination = denomination.lower()
    if denomination not in conversion_rates:
        await ctx.send("Invalid denomination. Use cp, sp, ep, gp, or pp.")
        return

    share_copper = to_copper(amount, denomination) // len(members)
    data = load_data()

    for member in members:
        user_id = str(member.id)
        if user_id in data:
            user_balance = data[user_id]
            user_balance_copper = sum([to_copper(user_balance[d], d) for d in user_balance])
            new_balance = user_balance_copper + share_copper
            data[user_id] = from_copper(new_balance)
        else:
            data[user_id] = from_copper(share_copper)

    save_data(data)
    member_names = ', '.join([member.display_name for member in members])
    await ctx.send(f'{amount} {denomination} split between {member_names}. Each receives {format_currency(from_copper(share_copper))}.')


# Initialize the party bank in data if it doesn't exist
def initialize_party_bank(data):
    if 'party_bank' not in data:
        data['party_bank'] = from_copper(0)

# Command to check the party bank balance
@bot.command()
async def bank_balance(ctx):
    data = load_data()
    initialize_party_bank(data)
    bank_balance = data['party_bank']
    await ctx.send(f'The party bank has: {format_currency(bank_balance)}.')

# Command to deposit money into the party bank
@bot.command()
async def deposit(ctx, amount: int, denomination: str):
    denomination = denomination.lower()
    if denomination not in conversion_rates:
        await ctx.send("Invalid denomination. Use cp, sp, ep, gp, or pp.")
        return
    
    data = load_data()
    initialize_party_bank(data)
    copper_amount = to_copper(amount, denomination)
    
    # Add to the party bank
    bank_balance_copper = sum([to_copper(data['party_bank'][d], d) for d in data['party_bank']])
    new_balance = bank_balance_copper + copper_amount
    data['party_bank'] = from_copper(new_balance)
    
    save_data(data)
    await ctx.send(f'{amount} {denomination} deposited into the party bank. New balance: {format_currency(data["party_bank"])}.')

# Command to withdraw money from the party bank
@bot.command()
async def withdraw(ctx, amount: int, denomination: str):
    denomination = denomination.lower()
    if denomination not in conversion_rates:
        await ctx.send("Invalid denomination. Use cp, sp, ep, gp, or pp.")
        return
    
    data = load_data()
    initialize_party_bank(data)
    copper_amount = to_copper(amount, denomination)
    
    # Check if there's enough in the bank
    bank_balance_copper = sum([to_copper(data['party_bank'][d], d) for d in data['party_bank']])
    if copper_amount > bank_balance_copper:
        await ctx.send("Not enough money in the party bank to withdraw that amount.")
        return

    # Subtract from the party bank
    new_balance = bank_balance_copper - copper_amount
    data['party_bank'] = from_copper(new_balance)

    save_data(data)
    await ctx.send(f'{amount} {denomination} withdrawn from the party bank. New balance: {format_currency(data["party_bank"])}.')

# Existing commands for individual balances, add_money, subtract_money, etc.



# Below is declaring the Bot key and the Channel ID. 
# Step 1: Prompt the user for the folder path where the files are stored
folder_path = input("Enter the folder path where the bot key and channel ID files are stored: ")

# Step 2: Within the folder you are directing, ensure that the Bot_Key.txt and Channel_ID.txt are present, it will automatically pull them.
bot_key_filename = "Bot_Key.txt"
channel_id_filename = "Channel_ID.txt"

# Step 3: Construct the full paths to the files
bot_key_path = f"{folder_path}/{bot_key_filename}"
channel_id_path = f"{folder_path}/{channel_id_filename}"

# Step 4: Read the bot key and channel ID from the files
with open(bot_key_path, 'r') as bot_key_file:
    bot_key = bot_key_file.read().strip()

with open(channel_id_path, 'r') as channel_id_file:
    CHANNEL_ID = channel_id_file.read().strip()

# Step 5: Run the bot with the actual bot key
bot.run(bot_key)




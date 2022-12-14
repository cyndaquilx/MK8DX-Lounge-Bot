import discord

website_url = "https://www.mk8dx-lounge.com"
bot_channels = [741906846209671223]

#id of the results channels for each tier
channels = {"X": 698153967820996639,
            "S": 445716741830737920,
            "A": 445570804915109889,
            "AB": 817605040105717830,
            "B": 445570790151421972,
            "BC": 874395278520774678,
            "C": 445570768269475840,
            "CD": 874395385525854318,
            "D": 445570755657465856,
            "DE": 874395482045153322,
            "E": 445716908923420682,
            "EF": 874395541482647592,
            "F": 796870494405394472,
            "FG": 1052415968401444894,
            "G": 1052416008201175060,
            "SQ": 772531512410636289}

#contains the emoji ID and role ID for each rank in the server;
#rank names should match up with getRank function below
ranks = {
    "Grandmaster": {
        "emoji": "<:grandmaster:731579876846338161>",
        "roleid": 874340227177668699,
        "color": "#A3022C",
        "url": "https://i.imgur.com/EWXzu2U.png"},
    "Master": {
        "emoji": "<:master:731597294914502737>",
        "roleid": 874340298048831578,
        "color": "#D9E1F2",
        "url": "https://i.imgur.com/3yBab63.png"},
    "Diamond 2": {
        "emoji": "<:diamond:731579813386780722> 2",
        "roleid": 874340374083154030,
        "color": "#BDD7EE",
        "url": "https://i.imgur.com/RDlvdvA.png"},
    "Diamond 1": {
        "emoji": "<:diamond:731579813386780722> 1",
        "roleid": 874340476080238612,
        "color": "#BDD7EE",
        "url": "https://i.imgur.com/RDlvdvA.png"},
    "Ruby 2": {
        "emoji": "Ruby 2",
        "roleid": 1052416345628754020,
        "color": "#D51C5E",
        "url": "https://i.imgur.com/7kr4AEs.png"},
    "Ruby 1": {
        "emoji": "Ruby 1",
        "roleid": 1052416501732356167,
        "color": "#D51C5E",
        "url": "https://i.imgur.com/7kr4AEs.png"},
    "Sapphire 2": {
        "emoji": "<:sapphire:731579851802411068> 2",
        "roleid": 874340543923118130,
        "color": "#286CD3",
        "url": "https://i.imgur.com/bXEfUSV.png"},
    "Sapphire 1": {
        "emoji": "<:sapphire:731579851802411068> 1",
        "roleid": 950073170071781467,
        "color": "#286CD3",
        "url": "https://i.imgur.com/bXEfUSV.png"},
    "Platinum 2": {
        "emoji": "<:platinum:542204444302114826> 2",
        "roleid": 874340619751931934,
        "color": "#3FABB8",
        "url": "https://i.imgur.com/8v8IjHE.png"},
    "Platinum 1": {
        "emoji": "<:platinum:542204444302114826> 1",
        "roleid": 874340697887637535,
        "color": "#3FABB8",
        "url": "https://i.imgur.com/8v8IjHE.png"},
    "Gold 2": {
        "emoji": "<:gold:731579798111125594> 2",
        "roleid": 874340761964003389,
        "color": "#FFD966",
        "url": "https://i.imgur.com/6yAatOq.png"},
    "Gold 1": {
        "emoji": "<:gold:731579798111125594> 1",
        "roleid": 874340824861794324,
        "color": "#FFD966",
        "url": "https://i.imgur.com/6yAatOq.png"},
    "Silver 2": {
        "emoji": "<:silver:731579781828575243> 2",
        "roleid": 874340970764861511,
        "color": "#D9D9D9",
        "url": "https://i.imgur.com/xgFyiYa.png"},
    "Silver 1": {
        "emoji": "<:silver:731579781828575243> 1",
        "roleid": 874341090579349504,
        "color": "#D9D9D9",
        "url": "https://i.imgur.com/xgFyiYa.png"},
    "Bronze 2": {
        "emoji": "<:bronze:731579759712010320> 2",
        "roleid": 874341171399376896,
        "color": "#C65911",
        "url": "https://i.imgur.com/DxFLvtO.png"},
    "Bronze 1": {
        "emoji": "<:bronze:731579759712010320> 1",
        "roleid": 874342922601005066,
        "color": "#C65911",
        "url": "https://i.imgur.com/DxFLvtO.png"},
    "Iron 2": {
        "emoji": "<:iron:731579735544430703> 2",
        "roleid": 874343078784274502,
        "color": "#817876",
        "url": "https://i.imgur.com/AYRMVEu.png"},
    "Iron 1": {
        "emoji": "<:iron:731579735544430703> 1",
        "roleid": 874343146316783708,
        "color": "#817876",
        "url": "https://i.imgur.com/AYRMVEu.png"}
    }

place_MMRs = {"gold": 7500,
              "silver": 5500,
              "bronze": 3500,
              "iron": 1500}

place_scores = {130: "silver",
                90: "bronze",
                0: "iron"}
                

#this is where you define the MMR thresholds for each rank
def getRank(mmr: int):
    if mmr >= 17000:
        return("Grandmaster")
    elif mmr >= 16000:
        return("Master")
    elif mmr >= 15000:
        return("Diamond 2")
    elif mmr >= 14000:
        return("Diamond 1")
    elif mmr >= 13000:
        return("Ruby 2")
    elif mmr >= 12000:
        return("Ruby 1")
    elif mmr >= 11000:
        return("Sapphire 2")
    elif mmr >= 10000:
        return("Sapphire 1")
    elif mmr >= 9000:
        return("Platinum 2")
    elif mmr >= 8000:
        return("Platinum 1")
    elif mmr >= 7000:
        return("Gold 2")
    elif mmr >= 6000:
        return("Gold 1")
    elif mmr >= 5000:
        return("Silver 2")
    elif mmr >= 4000:
        return("Silver 1")
    elif mmr >= 3000:
        return("Bronze 2")
    elif mmr >= 2000:
        return("Bronze 1")
    elif mmr >= 1000:
        return("Iron 2")
    else:
        return ("Iron 1")

placementRoleID = 730980761322389504
nameChangeLog = 489084104030158856
nameRequestLog = 1003155257792151743
strike_log_channel = 976664760873545728
player_role_ID = 976601946888736829

def get_players_from_table(table):
    players = []
    for team in table['teams']:
        for score in team['scores']:
            players.append(score)
    return players

def is_player_in_table(discordId:int, table):
    players = get_players_from_table(table)
    for player in players:
        if str(discordId) == player['playerDiscordId']:
            return True
    return False

def get_table_embed(table, bot):
    e = discord.Embed(title="Mogi Table", colour=int("0A2D61", 16))
    e.add_field(name="ID", value=table['id'])
    e.add_field(name="Tier", value=table['tier'])
    e.add_field(name="Submitted by", value=f"<@{table['authorId']}>")
    e.add_field(name="View on website", value=bot.site_creds["website_url"] + f"/TableDetails/{table['id']}")
    e.set_image(url=f"{bot.site_creds['website_url']}{table['url']}")
    return e

#ignore if end user
#taken from gspread.utils:
#https://github.com/burnash/gspread/blob/master/gspread/utils.py
##def rowcol_to_a1(row, col):
##    row = int(row)
##    col = int(col)
##
##    div = col
##    column_label = ''
##
##    while div:
##        (div, mod) = divmod(div, 26)
##        if mod == 0:
##            mod = 26
##            div -= 1
##        column_label = chr(mod + 64) + column_label
##
##    label = '%s%s' % (column_label, row)
##
##    return label


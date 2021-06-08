website_url = "https://www.mk8dx-lounge.com"
bot_channels = [741906846209671223]

#id of the results channels for each tier
channels = {"X": 698153967820996639,
            "S": 445716741830737920,
            "A": 445570804915109889,
            "AB": 817605040105717830,
            "B": 445570790151421972,
            "C": 445570768269475840,
            "D": 445570755657465856,
            "E": 445716908923420682,
            "F": 796870494405394472,
            "SQ": 772531512410636289}

#contains the emoji ID and role ID for each rank in the server;
#rank names should match up with getRank function below
ranks = {
    "Grandmaster": {
        "emoji": "<:grandmaster:731579876846338161>",
        "roleid": 730976842898735195,
        "color": "#A3022C",
        "url": "https://i.imgur.com/EWXzu2U.png"},
    "Master": {
        "emoji": "<:master:731597294914502737>",
        "roleid": 445707276385386497,
        "color": "#D9E1F2",
        "url": "https://i.imgur.com/3yBab63.png"},
    "Diamond": {
        "emoji": "<:diamond:731579813386780722>",
        "roleid": 445404401989844994,
        "color": "#BDD7EE",
        "url": "https://i.imgur.com/RDlvdvA.png"},
    "Sapphire": {
        "emoji": "<:sapphire:731579851802411068>",
        "roleid": 730976660681130075,
        "color": "#286CD3",
        "url": "https://i.imgur.com/bXEfUSV.png"},
    "Platinum": {
        "emoji": "<:platinum:542204444302114826>",
        "roleid": 445544728700649472,
        "color": "#3FABB8",
        "url": "https://i.imgur.com/8v8IjHE.png"},
    "Gold": {
        "emoji": "<:gold:731579798111125594>",
        "roleid": 445404441110380545,
        "color": "#FFD966",
        "url": "https://i.imgur.com/6yAatOq.png"},
    "Silver": {
        "emoji": "<:silver:731579781828575243>",
        "roleid": 445544735638159370,
        "color": "#D9D9D9",
        "url": "https://i.imgur.com/xgFyiYa.png"},
    "Bronze": {
        "emoji": "<:bronze:731579759712010320>",
        "roleid": 445404463092596736,
        "color": "#C65911",
        "url": "https://i.imgur.com/DxFLvtO.png"},
    "Iron 2": {
        "emoji": "<:iron:731579735544430703> 2",
        "roleid": 730976738007580672,
        "color": "#817876",
        "url": "https://i.imgur.com/AYRMVEu.png"},
    "Iron 1": {
        "emoji": "<:iron:731579735544430703> 1",
        "roleid": 805288798879481886,
        "color": "#817876",
        "url": "https://i.imgur.com/AYRMVEu.png"}
    }

place_MMRs = {"gold": 7500,
              "silver": 6000,
              "bronze": 4500,
              "iron2": 3000,
              "iron1": 1750}

#this is where you define the MMR thresholds for each rank
def getRank(mmr: int):
    if mmr >= 14500:
        return("Grandmaster")
    elif mmr >= 13000:
        return("Master")
    elif mmr >= 11500:
        return("Diamond")
    elif mmr >= 10000:
        return("Sapphire")
    elif mmr >= 8500:
        return("Platinum")
    elif mmr >= 7000:
        return("Gold")
    elif mmr >= 5500:
        return("Silver")
    elif mmr >= 4000:
        return("Bronze")
    elif mmr >= 2000:
        return("Iron 2")
    else:
        return ("Iron 1")

placementRoleID = 730980761322389504

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


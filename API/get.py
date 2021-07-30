import aiohttp
import json

from datetime import datetime, timedelta

headers = {'Content-type': 'application/json'}

with open('credentials.json', 'r') as cjson:
    creds = json.load(cjson)


async def getStrikes(name):
    fromDate = datetime.utcnow() - timedelta(days=30)
    base_url = creds['website_url'] + '/api/penalty/list?'
    request_text = ("name=%s&isStrike=true&from=%s"
                    % (name, fromDate.isoformat()))
    request_url = base_url + request_text
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(creds["username"], creds["password"])) as session:
        async with session.get(request_url,headers=headers) as resp:
            if resp.status != 200:
                return False
            strikes = await resp.json()
            return strikes
    

async def checkNames(names):
    base_url = creds['website_url'] + '/api/player?'
    on_lbs = []
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(creds["username"], creds["password"])) as session:
        for name in names:
            request_text = "name=%s" % name
            request_url = base_url + request_text
            async with session.get(request_url,headers=headers) as resp:
                if resp.status != 200:
                    on_lbs.append(False)
                    continue
                playerData = await resp.json()
                on_lbs.append(playerData["name"])
    return on_lbs

async def getPlayer(name):
    base_url = creds['website_url'] + '/api/player?'
    request_text = "name=%s" % name
    request_url = base_url + request_text
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(creds["username"], creds["password"])) as session:
        async with session.get(request_url,headers=headers) as resp:
            if resp.status != 200:
                return None
            player = await resp.json()
            return player

async def getPlayerFromMKC(mkcid):
    base_url = creds['website_url'] + '/api/player?'
    request_text = "mkcId=%d" % mkcid
    request_url = base_url + request_text
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(creds["username"], creds["password"])) as session:
        async with session.get(request_url,headers=headers) as resp:
            if resp.status != 200:
                return None
            player = await resp.json()
            return player

async def getPlayerFromDiscord(discordid):
    base_url = creds['website_url'] + '/api/player?'
    request_text = f"discordId={discordid}"
    request_url = base_url + request_text
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(creds["username"], creds["password"])) as session:
        async with session.get(request_url,headers=headers) as resp:
            if resp.status != 200:
                return None
            player = await resp.json()
            return player

async def getPlayerInfo(name):
    base_url = creds['website_url'] + '/api/player/details?'
    request_text = "name=%s" % name
    request_url = base_url + request_text
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(creds["username"], creds["password"])) as session:
        async with session.get(request_url,headers=headers) as resp:
            if resp.status != 200:
                return None
            playerData = await resp.json()
            return playerData

async def getTable(tableID):
    base_url = creds['website_url'] + '/api/table?'
    request_text = "tableId=%d" % tableID
    request_url = base_url + request_text
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(creds["username"], creds["password"])) as session:
        async with session.get(request_url,headers=headers) as resp:
            if resp.status != 200:
                return False
            table = await resp.json()
            return table


async def getPending():
    request_url = creds['website_url'] + '/api/table/unverified'
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(creds["username"], creds["password"])) as session:
        async with session.get(request_url,headers=headers) as resp:
            if resp.status != 200:
                return False
            tables = await resp.json()
            return tables
    

import aiohttp
from models import Table, WebsiteCredentials, Player, PlayerDetailed, NameChangeRequest, ListPlayer, Penalty

headers = {'Content-type': 'application/json'}

# with open('credentials.json', 'r') as cjson:
#     creds = json.load(cjson)


async def getStrikes(credentials: WebsiteCredentials, name: str):
    # fromDate = datetime.now(timezone.utc) - timedelta(days=30)
    request_url = f"{credentials.url}/api/penalty/list?name={name}&isStrike=true"
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(credentials.username, credentials.password)) as session:
        async with session.get(request_url,headers=headers) as resp:
            if resp.status != 200:
                return None, await resp.text()
            body = await resp.json()
            strikes = Penalty.from_list_api_response(body)
            return strikes, None

# async def checkNames(names):
#     base_url = creds['website_url'] + '/api/player?'
#     on_lbs = []
#     async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(creds["username"], creds["password"])) as session:
#         for name in names:
#             request_text = "name=%s" % name
#             request_url = base_url + request_text
#             async with session.get(request_url,headers=headers) as resp:
#                 if resp.status != 200:
#                     on_lbs.append(False)
#                     continue
#                 playerData = await resp.json()
#                 on_lbs.append(playerData["name"])
#     return on_lbs

async def getPlayers(credentials: WebsiteCredentials, names: list[str]):
    base_url = f"{credentials.url}/api/player"
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(credentials.username, credentials.password)) as session:
        players: list[Player | None] = []
        for name in names:
            request_url = f"{base_url}?name={name}"
            async with session.get(request_url, headers=headers) as resp:
                if resp.status != 200:
                    players.append(None)
                    continue
                body = await resp.json()
                player = Player.from_api_response(body)
                players.append(player)
        return players

# async def getPlayer(name):
#     base_url = creds['website_url'] + '/api/player?'
#     request_text = "name=%s" % name
#     request_url = base_url + request_text
#     async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(creds["username"], creds["password"])) as session:
#         async with session.get(request_url,headers=headers) as resp:
#             if resp.status != 200:
#                 return None
#             player = await resp.json()
#             return player
        
async def getPlayerNew(credentials: WebsiteCredentials, name: str):
    request_url = f"{credentials.url}/api/player?name={name}"
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(credentials.username, credentials.password)) as session:
        async with session.get(request_url,headers=headers) as resp:
            if resp.status != 200:
                return None
            body = await resp.json()
            player = Player.from_api_response(body)
            return player

async def getPlayerFromMKC(credentials: WebsiteCredentials, mkc_id: int):
    request_url = f"{credentials.url}/api/player?mkcId={mkc_id}"
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(credentials.username, credentials.password)) as session:
        async with session.get(request_url,headers=headers) as resp:
            if resp.status != 200:
                return None
            body = await resp.json()
            player = Player.from_api_response(body)
            return player

# async def getPlayerFromDiscord(discordid):
#     base_url = creds['website_url'] + '/api/player?'
#     request_text = f"discordId={discordid}"
#     request_url = base_url + request_text
#     async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(creds["username"], creds["password"])) as session:
#         async with session.get(request_url,headers=headers) as resp:
#             if resp.status != 200:
#                 return None
#             player = await resp.json()
#             return player
        
async def getPlayerFromDiscordNew(credentials: WebsiteCredentials, discord_id):
    request_url = f"{credentials.url}/api/player?discordId={discord_id}"
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(credentials.username, credentials.password)) as session:
        async with session.get(request_url,headers=headers) as resp:
            if resp.status != 200:
                return None
            body = await resp.json()
            player = Player.from_api_response(body)
            return player

# async def getPlayerInfo(name):
#     base_url = creds['website_url'] + '/api/player/details?'
#     request_text = "name=%s" % name
#     request_url = base_url + request_text
#     async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(creds["username"], creds["password"])) as session:
#         async with session.get(request_url,headers=headers) as resp:
#             if resp.status != 200:
#                 return None
#             playerData = await resp.json()
#             return playerData
        
async def getPlayerDetails(credentials: WebsiteCredentials, name: str):
    request_url = f"{credentials.url}/api/player/details?name={name}"
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(credentials.username, credentials.password)) as session:
        async with session.get(request_url,headers=headers) as resp:
            if resp.status != 200:
                return None
            playerData = await resp.json()
            player = PlayerDetailed.from_api_response(playerData)
            return player
        
async def getPlayerDetailsFromDiscord(credentials: WebsiteCredentials, discord_id: int):
    request_url = f"{credentials.url}/api/player/details?discordId={discord_id}"
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(credentials.username, credentials.password)) as session:
        async with session.get(request_url,headers=headers) as resp:
            if resp.status != 200:
                return None
            playerData = await resp.json()
            player = PlayerDetailed.from_api_response(playerData)
            return player

# async def getTable(tableID):
#     base_url = creds['website_url'] + '/api/table?'
#     request_text = "tableId=%d" % tableID
#     request_url = base_url + request_text
#     async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(creds["username"], creds["password"])) as session:
#         async with session.get(request_url,headers=headers) as resp:
#             if resp.status != 200:
#                 return False
#             table = await resp.json()
#             return table
        
async def getTableClass(credentials: WebsiteCredentials, table_id: int):
    request_url = f"{credentials.url}/api/table?tableId={table_id}"
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(credentials.username, credentials.password)) as session:
        async with session.get(request_url,headers=headers) as resp:
            if resp.status != 200:
                return None
            table = await resp.json()
            return Table.from_api_response(table)

async def getPending(credentials: WebsiteCredentials):
    request_url = f"{credentials.url}/api/table/unverified"
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(credentials.username, credentials.password)) as session:
        async with session.get(request_url,headers=headers) as resp:
            if resp.status != 200:
                return None
            body = await resp.json()
            tables = Table.from_list_api_response(body)
            return tables
    
async def getPlayerList(credentials: WebsiteCredentials):
    request_url = f"{credentials.url}/api/player/list"
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(credentials.username, credentials.password)) as session:
        async with session.get(request_url,headers=headers) as resp:
            if resp.status != 200:
                return None
            body = await resp.json()
            players = ListPlayer.from_list_api_response(body)
            return players

async def getPendingNameChanges(credentials: WebsiteCredentials):
    request_url = f"{credentials.url}/api/player/listPendingNameChanges"
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(credentials.username, credentials.password)) as session:
        async with session.get(request_url,headers=headers) as resp:
            if resp.status != 200:
                return None
            body = await resp.json()
            changes = NameChangeRequest.list_from_api_response(body)
            return changes

import aiohttp
import json
from models import TableBasic, Table, WebsiteCredentials, Player, NameChangeRequest, Penalty, Bonus

headers = {'Content-type': 'application/json'}

with open('credentials.json', 'r') as cjson:
    creds = json.load(cjson)

async def createBonus(credentials: WebsiteCredentials, name: str, amount: int):
    request_url = f"{credentials.url}/api/bonus/create?name={name}&amount={amount}"
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(credentials.username, credentials.password)) as session:
        async with session.post(request_url,headers=headers) as resp:
            if resp.status != 201:
                error = await resp.text()
                return None, error
            body = await resp.json()
            bonus = Bonus.from_api_response(body)
            return bonus, None

async def bonusMKC(mkc:int, amount:int):
    base_url = creds['website_url'] + '/api/bonus/create?'
    request_text = "mkcId=%d&amount=%d" % (mkc, amount)
    request_url = base_url + request_text
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(creds["username"], creds["password"])) as session:
        async with session.post(request_url,headers=headers) as resp:
            if resp.status != 201:
                error = await resp.text()
                return False, error
            bonus = await resp.json()
            return True, bonus

async def createPenalty(credentials: WebsiteCredentials, name: str, amount: int, isStrike: bool):
    request_url = f"{credentials.url}/api/penalty/create?name={name}&amount={amount}"
    if isStrike:
        request_url += "&isStrike=true"
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(credentials.username, credentials.password)) as session:
        async with session.post(request_url, headers=headers) as resp:
            if resp.status == 404:
                error = "Player not found"
                return None, error
            if resp.status != 201:
                error = await resp.text()
                return None, error
            body = await resp.json()
            penalty = Penalty.from_api_response(body)
            return penalty, None

async def deletePenalty(credentials: WebsiteCredentials, pen_id: int):
    request_url = f"{credentials.url}/api/penalty?id={pen_id}"
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(credentials.username, credentials.password)) as session:
        async with session.delete(request_url,headers=headers) as resp:
            if resp.status == 200:
                return True, None
            return False, resp.status

async def createNewPlayer(credentials: WebsiteCredentials, mkcid:int, name, discordid=None):
    request_url = f"{credentials.url}/api/player/create?name={name}&mkcid={mkcid}"
    if discordid is not None:
        request_url += f"&discordId={discordid}"
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(credentials.username, credentials.password)) as session:
        async with session.post(request_url,headers=headers) as resp:
            if resp.status != 201:
                error = await resp.text()
                return False, error
            body = await resp.json()
            player = Player.from_api_response(body)
            return True, player

async def createPlayerWithMMR(credentials: WebsiteCredentials, mkcid:int, mmr:int, name, discordid=None):
    request_url = f"{credentials.url}/api/player/create?name={name}&mkcid={mkcid}&mmr={mmr}"
    if discordid is not None:
        request_url += f"&discordId={discordid}"
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(credentials.username, credentials.password)) as session:
        async with session.post(request_url,headers=headers) as resp:
            if resp.status != 201:
                error = await resp.text()
                return False, error
            body = await resp.json()
            player = Player.from_api_response(body)
            return True, player

async def batchAddPlayers(names, mkcIDs, mmrs):
    base_url = creds['website_url'] + '/api/player/create?'
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(creds["username"], creds["password"])) as session:
        for i in range(len(names)):
            request_text = "name=%s&mkcid=%d" % (names[i], mkcIDs[i])
            if mmrs[i] is not None:
                request_text += "&mmr=%d" % mmrs[i]
            request_url = base_url + request_text
            async with session.post(request_url,headers=headers) as resp:
                print(await resp.text())
    
async def placePlayer(mmr:int, name):
    base_url = creds['website_url'] + '/api/player/placement?'
    request_text = "name=%s&mmr=%d" % (name, mmr)
    request_url = base_url + request_text
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(creds["username"], creds["password"])) as session:
        async with session.post(request_url,headers=headers) as resp:
            if resp.status != 201:
                error = await resp.text()
                return False, error
            player = await resp.json()
            return True, player
        
async def placePlayerNew(credentials: WebsiteCredentials, mmr:int, name:str, force=False):
    request_url = f"{credentials.url}/api/player/placement?name={name}&mmr={mmr}"
    if force:
        request_url += "&force=true"
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(credentials.username, credentials.password)) as session:
        async with session.post(request_url,headers=headers) as resp:
            if resp.status != 201:
                error = await resp.text()
                return False, error
            body = await resp.json()
            player = Player.from_api_response(body)
            return True, player

async def forcePlace(mmr:int, name):
    base_url = creds['website_url'] + '/api/player/placement?'
    request_text = "name=%s&mmr=%d&force=true" % (name, mmr)
    request_url = base_url + request_text
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(creds["username"], creds["password"])) as session:
        async with session.post(request_url,headers=headers) as resp:
            if resp.status != 201:
                error = await resp.text()
                return False, error
            player = await resp.json()
            return True, player

async def updatePlayerName(credentials: WebsiteCredentials, oldName: str, newName: str):
    request_url = f"{credentials.url}/api/player/update/name?name={oldName}&newName={newName}"
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(credentials.username, credentials.password)) as session:
        async with session.post(request_url,headers=headers) as resp:
            if resp.status == 204:
                return None
            if resp.status == 404:
                return("User with the current name doesn't exist")
            if resp.status == 400:
                return("User with that new name already exists")

async def updateMKCid(credentials: WebsiteCredentials, name, newID):
    request_url = f"{credentials.url}/api/player/update/mkcId?name={name}&newMkcId={newID}"
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(credentials.username, credentials.password)) as session:
        async with session.post(request_url,headers=headers) as resp:
            if resp.status == 404:
                return("Could not find user specified")
            if resp.status != 204:
                return await resp.text()
            return True          

async def deleteTable(tableID):
    base_url = creds['website_url'] + '/api/table?'
    request_text = "tableId=%d" % (tableID)
    request_url = base_url + request_text
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(creds["username"], creds["password"])) as session:
        async with session.delete(request_url,headers=headers) as resp:
            if resp.status == 200:
                return True
            return resp.status

async def createTable(tier, names, scores, authorid=0):
    request_url = creds['website_url'] + '/api/table/create?'
    request_json = {"tier": tier,
                    "scores": []}
    if authorid != 0:
        request_json["authorId"] = str(authorid)
    for i in range(len(names)):
        for j in range(len(names[i])):
            playerDetails = {"playerName": names[i][j],
                             "team": i,
                             "score": scores[i][j]}
            request_json["scores"].append(playerDetails)
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(creds["username"], creds["password"])) as session:
        async with session.post(request_url,headers=headers,json=request_json) as resp:
            if resp.status != 201:
                error = await resp.text()
                return False, error
            returnjson = await resp.json()
            return True, returnjson
        
async def createTableFromClass(table: TableBasic):
    request_url = creds['website_url'] + '/api/table/create?'
    body = table.to_submission_format()
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(creds["username"], creds["password"])) as session:
        async with session.post(request_url,headers=headers,json=body) as resp:
            if resp.status != 201:
                error = await resp.text()
                return None, error
            returnjson = await resp.json()
            table = Table.from_api_response(returnjson)
            return table, None

async def setMultipliers(tableid, multipliers):
    base_url = creds['website_url'] + '/api/table/setMultipliers?'
    request_text = 'tableId=%d' % tableid
    request_url = base_url + request_text
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(creds["username"], creds["password"])) as session:
        async with session.post(request_url,headers=headers,json=multipliers) as resp:
            if resp.status != 200:
                return(await resp.text())
            return True

async def setScores(tableid, scores):
    base_url = creds['website_url'] + '/api/table/setScores?'
    request_text = 'tableId=%d' % tableid
    request_url = base_url + request_text
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(creds["username"], creds["password"])) as session:
        async with session.post(request_url,headers=headers,json=scores) as resp:
            if resp.status != 200:
                return(await resp.text())
            return True

async def setTableMessageId(tableid:int, msgid:int):
    base_url = creds['website_url'] + '/api/table/setTableMessageId?'
    request_text = 'tableId=%d&tableMessageId=%d' % (tableid, msgid)
    request_url = base_url + request_text
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(creds["username"], creds["password"])) as session:
        async with session.post(request_url,headers=headers) as resp:
            return

async def setUpdateMessageId(tableid:int, msgid:int):
    base_url = creds['website_url'] + '/api/table/setUpdateMessageId?'
    request_text = "tableId=%d&updateMessageId=%d" % (tableid, msgid)
    request_url = base_url + request_text
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(creds["username"], creds["password"])) as session:
        async with session.post(request_url,headers=headers) as resp:
            return

async def verifyTable(tableid:int):
    base_url = creds['website_url'] + '/api/table/verify?'
    request_text = "tableId=%d" % tableid
    request_url = base_url + request_text
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(creds["username"], creds["password"])) as session:
        async with session.post(request_url,headers=headers) as resp:
            if resp.status != 200:
                resp_text = await resp.text()
                error_msg = f"{resp.status} - {resp_text}"
                return False, error_msg
            table = await resp.json()
            return True, table

async def updateDiscord(name, discordid:int):
    base_url = creds['website_url'] + '/api/player/update/discordId?'
    request_text = f"name={name}&newDiscordId={discordid}"
    request_url = base_url + request_text
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(creds["username"], creds["password"])) as session:
        async with session.post(request_url,headers=headers) as resp:
            if int(resp.status/100) != 2:
                resp_text = await resp.text()
                error_msg = f"{resp.status} - {resp_text}"
                return False, error_msg
            return True, await resp.text()
        
async def updateDiscordNew(credentials: WebsiteCredentials, name, discord_id:int):
    request_url = f"{credentials.url}/api/player/update/discordId?name={name}&newDiscordId={discord_id}"
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(credentials.username, credentials.password)) as session:
        async with session.post(request_url,headers=headers) as resp:
            if int(resp.status/100) != 2:
                resp_text = await resp.text()
                error_msg = f"{resp.status} - {resp_text}"
                return False, error_msg
            return True, await resp.text()

async def hidePlayer(credentials: WebsiteCredentials, name):
    request_url = f"{credentials.url}/api/player/hide?name={name}"
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(credentials.username, credentials.password)) as session:
        async with session.post(request_url,headers=headers) as resp:
            if int(resp.status/100) != 2:
                resp_text = await resp.text()
                error_msg = f"{resp.status} - {resp_text}"
                return False, error_msg
            return True, await resp.text()

async def unhidePlayer(credentials: WebsiteCredentials, name):
    request_url = f"{credentials.url}/api/player/unhide?name={name}"
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(credentials.username, credentials.password)) as session:
        async with session.post(request_url,headers=headers) as resp:
            if int(resp.status/100) != 2:
                resp_text = await resp.text()
                error_msg = f"{resp.status} - {resp_text}"
                return False, error_msg
            return True, await resp.text()

async def refreshPlayerData(credentials: WebsiteCredentials, name):
    request_url = f"{credentials.url}/api/player/refreshRegistryData?name={name}"
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(credentials.username, credentials.password)) as session:
        async with session.post(request_url,headers=headers) as resp:
            if int(resp.status/100) != 2:
                resp_text = await resp.text()
                error_msg = f"{resp.status} - {resp_text}"
                return False, error_msg
            return True, await resp.text()

async def requestNameChange(credentials: WebsiteCredentials, old_name, new_name):
    request_url = f"{credentials.url}/api/player/requestNameChange?name={old_name}&newName={new_name}"
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(credentials.username, credentials.password)) as session:
        async with session.post(request_url,headers=headers) as resp:
            if int(resp.status/100) != 2:
                resp_text = await resp.text()
                error_msg = f"{resp.status} - {resp_text}"
                return False, error_msg
            return True, await resp.json()

async def setNameChangeMessageId(credentials: WebsiteCredentials, current_name, message_id):
    request_url = f"{credentials.url}/api/player/setNameChangeMessageId?name={current_name}&messageId={message_id}"
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(credentials.username, credentials.password)) as session:
        async with session.post(request_url, headers=headers) as resp:
            if int(resp.status/100) != 2:
                resp_text = await resp.text()
                error_msg = f"{resp.status} - {resp_text}"
                return False, error_msg
            return True, await resp.text()

async def acceptNameChange(credentials: WebsiteCredentials, current_name: str):
    request_url = f"{credentials.url}/api/player/acceptNameChange?name={current_name}"
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(credentials.username, credentials.password)) as session:
        async with session.post(request_url, headers=headers) as resp:
            if int(resp.status/100) != 2:
                resp_text = await resp.text()
                error_msg = f"{resp.status} - {resp_text}"
                return None, error_msg
            body = await resp.json()
            name_change = NameChangeRequest.from_api_response(body)
            return name_change, None

async def rejectNameChange(credentials: WebsiteCredentials, current_name: str):
    request_url = f"{credentials.url}/api/player/rejectNameChange?name={current_name}"
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(credentials.username, credentials.password)) as session:
        async with session.post(request_url, headers=headers) as resp:
            if int(resp.status/100) != 2:
                resp_text = await resp.text()
                error_msg = f"{resp.status} - {resp_text}"
                return None, error_msg
            body = await resp.json()
            name_change = NameChangeRequest.from_api_response(body)
            return name_change, None
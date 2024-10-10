import aiohttp
import json
from models import TableBasic, Table

headers = {'Content-type': 'application/json'}

with open('credentials.json', 'r') as cjson:
    creds = json.load(cjson)

async def createBonus(name, amount):
    base_url = creds['website_url'] + '/api/bonus/create?'
    request_text = "name=%s&amount=%d" % (name, amount)
    request_url = base_url + request_text
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(creds["username"], creds["password"])) as session:
        async with session.post(request_url,headers=headers) as resp:
            if resp.status != 201:
                error = await resp.text()
                return False, error
            bonus = await resp.json()
            return True, bonus

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

async def createPenalty(name, amount, isStrike):
    base_url = creds['website_url'] + '/api/penalty/create?'
    request_text = "name=%s&amount=%d" % (name, amount)
    if isStrike is True:
        request_text += "&isStrike=true"
    request_url = base_url + request_text
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(creds["username"], creds["password"])) as session:
        async with session.post(request_url,headers=headers) as resp:
            if resp.status == 404:
                error = "Player not found"
                return False, error
            if resp.status != 201:
                error = await resp.text()
                return False, error
            pen = await resp.json()
            return True, pen

async def deletePenalty(penID):
    base_url = creds['website_url'] + '/api/penalty?'
    request_text = "id=%d" % (penID)
    request_url = base_url + request_text
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(creds["username"], creds["password"])) as session:
        async with session.delete(request_url,headers=headers) as resp:
            if resp.status == 200:
                return True
            return resp.status
    

async def createNewPlayer(mkcid:int, name, discordid=None):
    base_url = creds['website_url'] + '/api/player/create?'
    request_text = "name=%s&mkcid=%d" % (name, mkcid)
    if discordid is not None:
        request_text += f"&discordId={discordid}"
    request_url = base_url + request_text
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(creds["username"], creds["password"])) as session:
        async with session.post(request_url,headers=headers) as resp:
            if resp.status != 201:
                error = await resp.text()
                return False, error
            player = await resp.json()
            return True, player

async def createPlayerWithMMR(mkcid:int, mmr:int, name, discordid=None):
    base_url = creds['website_url'] + '/api/player/create?'
    request_text = "name=%s&mkcid=%d&mmr=%d" % (name, mkcid, mmr)
    if discordid is not None:
        request_text += f"&discordId={discordid}"
    request_url = base_url + request_text
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(creds["username"], creds["password"])) as session:
        async with session.post(request_url,headers=headers) as resp:
            if resp.status != 201:
                error = await resp.text()
                return False, error
            player = await resp.json()
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

async def updatePlayerName(oldName, newName):
    base_url = creds['website_url'] + '/api/player/update/name?'
    request_text = "name=%s&newName=%s" % (oldName, newName)
    request_url = base_url + request_text
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(creds["username"], creds["password"])) as session:
        async with session.post(request_url,headers=headers) as resp:
            if resp.status == 204:
                return True
            if resp.status == 404:
                return("User with the current name doesn't exist")
            if resp.status == 400:
                return("User with that new name already exists")

async def updateMKCid(name, newID):
    base_url = creds['website_url'] + '/api/player/update/mkcId?'
    request_text = "name=%s&newMkcId=%d" % (name, newID)
    request_url = base_url + request_text
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(creds["username"], creds["password"])) as session:
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
                #print(f"{resp.status} {await resp.text()}")
                resp_text = await resp.text()
                error_msg = f"{resp.status} - {resp_text}"
                return False, error_msg
            return True, await resp.text()

async def hidePlayer(name):
    base_url = creds['website_url'] + '/api/player/hide?'
    request_text = f"name={name}"
    request_url = base_url + request_text
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(creds["username"], creds["password"])) as session:
        async with session.post(request_url,headers=headers) as resp:
            if int(resp.status/100) != 2:
                resp_text = await resp.text()
                error_msg = f"{resp.status} - {resp_text}"
                return False, error_msg
            return True, await resp.text()

async def unhidePlayer(name):
    base_url = creds['website_url'] + '/api/player/unhide?'
    request_text = f"name={name}"
    request_url = base_url + request_text
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(creds["username"], creds["password"])) as session:
        async with session.post(request_url,headers=headers) as resp:
            if int(resp.status/100) != 2:
                resp_text = await resp.text()
                error_msg = f"{resp.status} - {resp_text}"
                return False, error_msg
            return True, await resp.text()

async def refreshPlayerData(name):
    base_url = creds['website_url'] + '/api/player/refreshRegistryData?'
    request_text = f"name={name}"
    request_url = base_url + request_text
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(creds["username"], creds["password"])) as session:
        async with session.post(request_url,headers=headers) as resp:
            if int(resp.status/100) != 2:
                resp_text = await resp.text()
                error_msg = f"{resp.status} - {resp_text}"
                return False, error_msg
            return True, await resp.text()

async def requestNameChange(old_name, new_name):
    base_url = creds['website_url'] + '/api/player/requestNameChange?'
    request_text = f"name={old_name}&newName={new_name}"
    request_url = base_url + request_text
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(creds["username"], creds["password"])) as session:
        async with session.post(request_url,headers=headers) as resp:
            if int(resp.status/100) != 2:
                resp_text = await resp.text()
                error_msg = f"{resp.status} - {resp_text}"
                return False, error_msg
            return True, await resp.json()

async def setNameChangeMessageId(current_name, message_id):
    base_url = creds['website_url'] + '/api/player/setNameChangeMessageId?'
    request_text = f"name={current_name}&messageId={message_id}"
    request_url = base_url + request_text
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(creds["username"], creds["password"])) as session:
        async with session.post(request_url,headers=headers) as resp:
            if int(resp.status/100) != 2:
                resp_text = await resp.text()
                error_msg = f"{resp.status} - {resp_text}"
                return False, error_msg
            return True, await resp.text()

async def acceptNameChange(current_name):
    base_url = creds['website_url'] + '/api/player/acceptNameChange?'
    request_text = f"name={current_name}"
    request_url = base_url + request_text
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(creds["username"], creds["password"])) as session:
        async with session.post(request_url,headers=headers) as resp:
            if int(resp.status/100) != 2:
                resp_text = await resp.text()
                error_msg = f"{resp.status} - {resp_text}"
                return False, error_msg
            return True, await resp.json()

async def rejectNameChange(current_name):
    base_url = creds['website_url'] + '/api/player/rejectNameChange?'
    request_text = f"name={current_name}"
    request_url = base_url + request_text
    async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(creds["username"], creds["password"])) as session:
        async with session.post(request_url,headers=headers) as resp:
            if int(resp.status/100) != 2:
                resp_text = await resp.text()
                error_msg = f"{resp.status} - {resp_text}"
                return False, error_msg
            return True, await resp.json()
import urllib3, asyncio, json, os, time
from dotenv import load_dotenv
import aiohttp
from aiohttp import ClientTimeout

# get opendota api key from .env file
load_dotenv('.ENV')
KEY = os.getenv('KEY')

#create http object for api requests
http = urllib3.PoolManager()

playerurl = "https://api.opendota.com/api/players/{}/matches?api_key={}"
matchurl = "https://api.opendota.com/api/matches/{}/?api_key={}"

data = {}
data['matches'] = []

timeout = ClientTimeout(total=0)

# pretty printing of json format
def jsonprint(j):
    print(json.dumps(j, indent=4, sort_keys=True))

# get a list of all the matches a player has participated in
def getMatchIDs(steamID):
    p = http.request("GET", playerurl.format(steamID, KEY))
    matchData = json.loads(p.data)
    matchIdList = []
    for match in matchData:
        matchIdList.append(match["match_id"])
    return matchIdList

def getUnrecordedIDs(steamID, forceUpdate):
    allMatches = getMatchIDs(steamID)
    unrecorded = []
    recorded = []
    if (not os.path.exists("{}.txt".format(steamID))) or forceUpdate:
        unrecorded = allMatches
    else:
        with open("{}.txt".format(steamID), 'r') as json_file:
            data = json.load(json_file)
            for recordedMatch in data["matches"]:
                if "players" in recordedMatch:
                    recorded.append(recordedMatch["match_id"])
            for match in allMatches:
                if not isinstance(match, int):
                    if "players" in recordedMatch:
                        if match["match_id"] not in recorded:
                            unrecorded.append(match["match_id"])
    return unrecorded

def GetChatData(steamID, matchData):
    with open('{}.txt'.format(steamID)) as json_file:
        data = matchData
        words = []
        for match in data["matches"]:
            if "players" in match:
                playerSlot = -1
                for player in match["players"]:
                    if player["account_id"] == int(steamID):
                        playerSlot = player["player_slot"]
                if match["chat"] != None:
                    for message in match["chat"]:
                        if "player_slot" in message:
                            if message["player_slot"] == playerSlot and message["type"] == "chat":
                                words.append((message["key"], match["match_id"]))
    return words


async def pullMatches(steamID, listOfMatchIDs):
    async with aiohttp.ClientSession(timeout=timeout) as session:
        tasks = []
        for ID in listOfMatchIDs:
            tasks.append(session.get(matchurl.format(ID, KEY), ssl=False))
            if len(tasks) > 100:
                responses = await asyncio.gather(*tasks)
                tasks = []
        responses = await asyncio.gather(*tasks)
        for response in responses:
            data["matches"].append(await response.json())
def main():
    steamID = input("Enter a steam32 account ID: ")

    force = input("Force update local files? (y/n): ")

    if force == "Y" or force == "y":
        forceUpdateBool = True
    elif force == "N" or force == "n":
        forceUpdateBool = False

    listOfMatchIDs = getUnrecordedIDs(steamID, forceUpdateBool)
    
    start = time.time()
    print("starting event loop")
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    groupsize = 100
    q = groupsize
    lasttime = time.time()
    while q < len(listOfMatchIDs):
        asyncio.run(pullMatches(steamID, listOfMatchIDs[q - groupsize:q]))
        print("{} - {} {:>20}".format(q-groupsize, q, time.time()-lasttime))
        q += groupsize
        lasttime = time.time()

    asyncio.run(pullMatches(steamID, listOfMatchIDs[q:len(listOfMatchIDs) - 1]))
    print("{} - {} {:>20}".format(q, len(listOfMatchIDs) - 1, time.time()-lasttime))

    end = time.time()
    totaltime = end - start
    print(totaltime)

    with open("{}.txt".format(steamID), 'w') as outfile:
        json.dump(GetChatData(steamID, data), outfile)

if __name__ == '__main__':
    main()

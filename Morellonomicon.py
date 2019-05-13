import discord
from riotwatcher import RiotWatcher, ApiError
import time
import random
from requests import get
from requests.exceptions import RequestException
from contextlib import closing
from bs4 import BeautifulSoup
import keys

watcher = RiotWatcher(keys.riotAPI)
champData = watcher.data_dragon.champions('9.6.1')

#Creating id dictionaries to reference
champion_key_dic = {}

for champ in champData['data']:
    champion_key_dic[champData['data'][champ]['key']] = champData['data'][champ]['name']

def simple_get(url):

    try:
        with closing(get(url, stream=True)) as resp:
            if is_good_response(resp):
                return resp.content
            else:
                return None

    except:
        print('Error during requests to {0} : {1}'.format(url, str(e)))
        return None


def is_good_response(resp):

    content_type = resp.headers['Content-Type'].lower()
    return (resp.status_code == 200
            and content_type is not None
            and content_type.find('html') > -1) 

def summoner_name_reconstructor(user_message):
    summonerName = ""
    
    for i in range(3, len(user_message)):

        if summonerName == "":
            summonerName = user_message[i]
        else:
            summonerName += " " + user_message[i]

    return summonerName


def region_converter(region):
    region = region.lower()
    
    if region == 'na':
        region = 'na1'
        
    elif region == 'euw':
        region = 'euw1'

    elif region == 'eun':
        region = 'eun1'
        
    else:
        region = "Morellonomicon error - region not found (na, )"

    return region



def mo_summoner(region, summonerName):

    summonerName = summonerName.lower()
    region = region_converter(region)
    
    if "Morellonomicon error" in region:
        return region
    
    try:
        summonerData = watcher.summoner.by_name(region, summonerName)
        try:
            for n in range(3):
                rankedData = watcher.league.positions_by_summoner(region, summonerData['id'])[0]
                if rankedData['queueType'] == "RANKED_SOLO_5x5":
                    break
        except:
            return summonerData['name'] + " has no ranked data to display this season"

        queueType = ""
        if rankedData['queueType'] == "RANKED_SOLO_5x5":
            queueType = "Ranked Solo"
        else:
            queueType = "Ranked Flex"

        output = rankedData['summonerName'] + "\n"
        output += "------------------------\n"
        output += queueType + "\n"
        output += rankedData['tier'] + " " + rankedData['rank'] + " - " + str(rankedData['leaguePoints']) + " LP\n"
        output += str(rankedData['wins']) + " Wins - " + str(rankedData['losses']) + " Losses\n"

        if rankedData['wins'] + rankedData['losses'] != 0:
            output += "Win Rate - " + str(rankedData['wins'] / (rankedData['wins'] + rankedData['losses']) * 100)[:4] + "%\n"
            
        else:
            output += "Win Rate - Hasn't played any games this season!\n"

        output += "------------------------\n"
        output += "Summoner Level - " + str(summonerData['summonerLevel'])
            
        return output
        
    except ApiError as err:
        if err.response.status_code == 429:
            print("")
        elif err.response.status_code == 404:
            return "Morellonomicon error - summoner not found (check name!)"
        

def mo_currentgame(region, summonerName):

    summonerName = summonerName.lower()
    region = region_converter(region)
    
    if "Morellonomicon error" in region:
        return region

    try:
        summonerData = watcher.summoner.by_name(region, summonerName)
        currentGameData = watcher.spectator.by_summoner(region, summonerData['id'])
        blueTeam = ":large_blue_circle: Blue Team :large_blue_circle:\n----------------------\n"
        redTeam = ":red_circle: Red Team :red_circle:\n----------------------\n"
        
        for i in range(len(currentGameData['participants'])):
            
            player = currentGameData['participants'][i]
            
            try:
                for n in range(3):
                    rankedData = watcher.league.positions_by_summoner(region, player['summonerId'])[0]
                    if rankedData['queueType'] == "RANKED_SOLO_5x5":
                        break
                
                if rankedData['wins'] + rankedData['losses'] != 0:
                    winrate = rankedData['wins'] / (rankedData['wins'] + rankedData['losses']) * 100
                else:
                    winrate = ""
                    
                rank = rankedData['tier'] + " " + rankedData['rank']
                if rankedData['queueType'] != "RANKED_SOLO_5x5":
                    rank += " (Flex)"
                rank += " - " + str(winrate)[:4] + "%"
                
                if winrate < 40:
                    siren(client)
                    rank += " :warning: "
                
            except:
                rank = "No ranked data"
            
            if currentGameData['participants'][i]['teamId'] == 100:
                blueTeam += champion_key_dic[str(player['championId'])] + " - " + player['summonerName'] + " - " + rank + "\n"
            else:
                redTeam += champion_key_dic[str(player['championId'])] + " - " + player['summonerName'] + " - " + rank + "\n"

        output = blueTeam + "\n"
        output += redTeam
        return output
        
    except ApiError as err:
        if err.response.status_code == 404:
            return "Morellonomicon error - summoner not currently in a game (check summoner name!)"

def mo_build(champion):
    championNameClean = champion.replace('-', ' ').title()
    html = simple_get('https://rankedboost.com/league-of-legends/build/' + champion +'/#item-build')

    if html == None:
        return "Morellonomicon error - champion not found"
    
    #Getting build overview
    htmlSoup = BeautifulSoup(html, 'html.parser')
    html = str(htmlSoup.find_all('div', {'class': 'rb-build-overview-wrap'}))
    
    htmlSoup = BeautifulSoup(html, 'html.parser')
    html = htmlSoup.find_all('div', {'class': 'rb-build-spells'})
    
    #Getting starting items
    htmlSoup = BeautifulSoup(str(html[3]), 'html.parser')
    startingItems = htmlSoup.find_all('img', {'class': 'rb-item-img'})
    startingItemsSection = ':point_right: Starting items:\n'
    for entry in startingItems:
        if 'items' in str(entry):
            item = str(entry).split('title="', 1)[1]
            item = item.split('"/>', 1)[0]
            startingItemsSection = startingItemsSection + "         • " + item + '\n'
    
    #Getting core build
    htmlSoup = BeautifulSoup(str(html[4]), 'html.parser')
    coreItems = htmlSoup.find_all('img', {'class': 'rb-item-img'})
    coreItemsSection = '\n:point_right: Core items:\n'
    for entry in coreItems:
        if 'items' in str(entry):
            item = str(entry).split('title="', 1)[1]
            item = item.split('"/>', 1)[0]
            coreItemsSection = coreItemsSection + "         • " + item + '\n'

    response = championNameClean + ' build:\n----------------------\n'
    response = response + startingItemsSection
    response = response + coreItemsSection
    return response

client = discord.Client()

@client.event
async def on_ready():
    print("Bot is running")
    await client.change_presence(game=discord.Game(name="For Demacia! | mo help"))

    #Finding out how many servers the bot is currently in
    numServers = 0
    for server in client.servers:
        numServers += 1
    print("Number of servers: " + str(numServers))

@client.event
async def on_server_join(server):
    for channel in server.channels:
        if channel.is_default:
            await client.send_message(channel, "Hello Summoners, type \"mo help\" to get started!")

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    
    elif message.content == "mo":
        await client.send_message(message.channel, "Try \"mo help\" to get a list of commands")
        
    elif message.content == "mo help":
        help_message = "mo summoner [na,euw,etc] [summoner name] --- Quick ranked summoner overview\n"
        help_message += "mo currentgame [na,euw,etc] [summoner name] --- Overview of players in this summoner's game\n"
        await client.send_message(message.channel, help_message)

    elif "mo summoner" in message.content:
        splitMessage = message.content.split(" ")
        
        if len(splitMessage) >= 4:
            region = splitMessage[2]
            summoner = summoner_name_reconstructor(splitMessage)
            summonerData = mo_summoner(region, summoner)
            
            await client.send_message(message.channel, summonerData)
                
        else:
            await client.send_message(message.channel, "Morellonomicon error - mo summoner [na,euw,etc] [summoner name]")

    elif "mo currentgame" in message.content:
        splitMessage = message.content.split(" ")

        if len(splitMessage) >= 4:
            region = splitMessage[2]
            summoner = summoner_name_reconstructor(splitMessage)
            currentGameData = mo_currentgame(region, summoner)

            if ":warning:" in currentGameData:
                voice_channel = message.author.voice_channel
                vc = await client.join_voice_channel(voice_channel)
                player = vc.create_ffmpeg_player('Danger Alarm Sound Effect.mp3', after=lambda: print('done'))
                player.start()
                startTime = time.time()
                endTime = time.time()

                while (endTime - startTime < 6.7):
                    endTime = time.time()
                await vc.disconnect()
                
            await client.send_message(message.channel, currentGameData)

        else:
            await client.send_message(message.channel, "Morellonomicon error - mo currentgame [na,euw,etc] [summoner name]")
            
    elif "mo build" in message.content:
        splitMessage = message.content.split(" ")
        champion = ''
        if len(splitMessage) >= 3:
            champion = splitMessage[2]
            for i in range(3, len(splitMessage)):
                champion = champion + '-' + splitMessage[i]

            championBuild = mo_build(champion) 
            await client.send_message(message.channel, championBuild)

    elif "mo luck" == message.content:
        coin = random.randint(0,1)
        if (coin == 0):
            await client.send_message(message.channel, "Red team will win.")
        else:
            await client.send_message(message.channel, "Blue team will win.")
        

client.run(keys.discordAPI)

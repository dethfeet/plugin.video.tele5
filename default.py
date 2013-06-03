import xbmcplugin
import xbmcgui

import sys
import urllib, urllib2
import re

import httplib

from pyamf import AMF0, AMF3

from pyamf import remoting
from pyamf.remoting.client import RemotingService

import urlresolver
import json

thisPlugin = int(sys.argv[1])

baseUrl = "http://www.tele5.de/play"

def mainPage():
    page = load_page(baseUrl)
    _regex_extractShows = re.compile("<table class=\"play hidden\">(.*?)</table>", re.DOTALL)
    shows = _regex_extractShows.search(page).group(1)

    _regex_extractShow = re.compile("<li>.*?href=\"(.*?)\".*?src=\"(.*?)\".*?<span>(.*?)</span>",re.DOTALL)
    
    for show in _regex_extractShow.finditer(shows):
        img = baseUrl+'/../'+show.group(2)
        title = unicode(show.group(3).replace("\n"," "), "latin-1")
        addDirectoryItem(title, parameters={"action":"show", "link":show.group(1)}, pic=img, folder=True)
    xbmcplugin.endOfDirectory(thisPlugin)

def showPage(link):
    link = urllib.unquote(link)
    css_class = urllib.unquote(link)[1:]

    page = load_page(baseUrl+'/../'+link)
    
    _regex_extractEpisodes = re.compile("<table class=\""+css_class+" hidden\">(.*?)</table>", re.DOTALL)
    episodes = _regex_extractEpisodes.search(page).group(1)
    
    _regex_extractEpisode = re.compile("<li>.*?href=\"(.*?)\".*?src=\"(.*?)\".*?alt=\"(.*?)\"",re.DOTALL)
    for episode in _regex_extractEpisode.finditer(episodes):
        img = baseUrl+'/../'+episode.group(2)
        title = episode.group(3).replace("\n"," ")
        addDirectoryItem(title, parameters={"action":"episode", "link":episode.group(1)}, pic=img, folder=False)
    xbmcplugin.endOfDirectory(thisPlugin)

def episodePage(link):
    link = urllib.unquote(link)
    episode = link[1:]
    clip_info = get_clip_info(episode)
    
    try:
        filename = clip_info[0]['filename']
        stream_url = clip_info[0]['path']
        item = xbmcgui.ListItem(path=stream_url)
        item.setProperty('PlayPath', filename); 
    except KeyError:
        print clip_info[0]['path']
        if clip_info[0]['path'] == "/":
            #YouTube oder Soundcloud
            _regexExtractIframe = re.compile("<iframe .*?src=\"(.*?)\".*?></iframe>")
            iframe_src = _regexExtractIframe.search(clip_info[0]['quelle']).group(1)
            print iframe_src
            if iframe_src.find('soundcloud') > -1:
                #Soundcloud
                _regexExtractSoundcloudId = re.compile("tracks%2F(.*?)&")
                soundcloudId = _regexExtractSoundcloudId.search(iframe_src).group(1)
                soundcloudPage = load_page("https://api.soundcloud.com/i1/tracks/"+soundcloudId+"/streams?client_id=0f8fdbbaa21a9bd18210986a7dc2d72c&format=json")
                soundcloudJson = json.loads(soundcloudPage)
                stream_url = soundcloudJson['http_mp3_128_url']
            else:
                #YouTube
                stream_url = urlresolver.resolve(iframe_src)
        else:
            stream_url = baseUrl+"/../"+clip_info[0]['path']
        item = xbmcgui.ListItem(path=stream_url)
        
    xbmcplugin.setResolvedUrl(thisPlugin, True, item)
    return False
                                  
def load_page(url):
    print url
    req = urllib2.Request(url)
    response = urllib2.urlopen(req)
    link = response.read()
    response.close()
    return link

def addDirectoryItem(name, parameters={}, pic="", folder=True):
    li = xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=pic)
    if not folder:
        li.setProperty('IsPlayable', 'true')
    url = sys.argv[0] + '?' + urllib.urlencode(parameters)
    return xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=li, isFolder=folder)
    
def get_params():
    param = []
    paramstring = sys.argv[2]
    if len(paramstring) >= 2:
        params = sys.argv[2]
        cleanedparams = params.replace('?', '')
        if (params[len(params) - 1] == '/'):
            params = params[0:len(params) - 2]
        pairsofparams = cleanedparams.split('&')
        param = {}
        for i in range(len(pairsofparams)):
            splitparams = {}
            splitparams = pairsofparams[i].split('=')
            if (len(splitparams)) == 2:
                param[splitparams[0]] = splitparams[1]
    
    return param

def build_amf_request(clip_name):
    env = remoting.Envelope(amfVersion=3)
    env.bodies.append(
        (
            "/1",
            remoting.Request(
                target="tele5.getContentPlayer",
                body=[clip_name],
                envelope=env
            )
        )
    )
    return env

def get_clip_info(clip_name):
    conn = httplib.HTTPConnection("www.tele5.de")
    envelope = build_amf_request(clip_name)
    conn.request("POST", "/gateway/gateway.php", str(remoting.encode(envelope).read()), {'content-type': 'application/x-amf'})
    response = conn.getresponse().read()
    response = remoting.decode(response).bodies[0][1].body
    return response

if not sys.argv[2]:
    mainPage()
else:
    params = get_params()
    if params['action'] == "show":
        showPage(params['link'])
    if params['action'] == "episode":
        episodePage(params['link'])

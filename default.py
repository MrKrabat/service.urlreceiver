# -*- coding: utf-8 -*-
# URLReceiver - Send URLs for playback directly on your Kodi device.
# Copyright (C) 2016 - 2017 MrKrabat
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import sys
import re
import socket

import xbmc
import xbmcaddon
import xbmcgui

try:
    import urlresolver
    urlresolverimport = True
except:
    urlresolverimport = False


# Constants
__addonid__      = "service.urlreceiver"
__settings__  = xbmcaddon.Addon(id=__addonid__)
__plugin__    = __settings__.getAddonInfo("name")
__version__   = __settings__.getAddonInfo("version")
__path__      = __settings__.getAddonInfo("path")
__port__       = __settings__.getSetting("port")
__regex__      = r"\.([a-zA-Z0-9]*)(?=\||\?|\#|\n|$)"


# function to send messages
def sendtoclient(socket, browser, message):
    if not browser:
        socket.send(message)
    else:
        if len(message) == 1:
            message = message + "<script>window.close();</script>"

        message = "HTTP/1.1 200 OK\nContent-Type: text/html\nAccess-Control-Allow-Origin: *\n\n" + message
        socket.sendall(message.encode())


# start program
if __name__ == '__main__':
    monitor = xbmc.Monitor()
    # get playable extensions
    __mediaext__  = tuple(str(xbmc.getSupportedMedia("video") + "|" + xbmc.getSupportedMedia("music")).split('|'))
    # read URLSender.html
    with open(__path__ + "/urlsender.html", "r") as myfile:
        __urlsender__ = myfile.read()

    try:
        # create listening socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((xbmc.getIPAddress(), int(__port__)))
        sock.listen(1)
        sock.setblocking(0)
        xbmc.log("[SERVICE] %s: Initializing version %s on port %s" % (__plugin__, __version__, __port__), xbmc.LOGDEBUG)
        xbmcgui.Dialog().notification(__plugin__, __settings__.getLocalizedString(30100), xbmcgui.NOTIFICATION_INFO)
    except socket.error:
        # unable to listen on port
        xbmc.log("[SERVICE] %s: Initializing version %s failed on port %s" % (__plugin__, __version__, __port__), xbmc.LOGFATAL)
        xbmcgui.Dialog().notification(__plugin__, __settings__.getLocalizedString(30101) % __port__, xbmcgui.NOTIFICATION_ERROR)
        sys.exit()

    # main loop
    while not monitor.abortRequested():
        # shutdown requested?
        if monitor.waitForAbort(0.20):
            break

        try:
            # wait for incoming connection
            connection, client_address = sock.accept()
            try:
                # receive message
                connection.settimeout(10.0)
                data = connection.recv(4096).rstrip().decode("utf-8")
                if data:
                    # test if client is browser
                    browser = False
                    if xbmc.getIPAddress() in data:
                        data = data.split("\n", 1)[0]
                        data = data[13:-9].strip()
                        browser = True
                        if not data or data == "ico":
                            # send webinterface
                            sendtoclient(connection, browser, __urlsender__)
                            continue

                    # Debug: log URL
                    xbmc.log("[SERVICE] %s: URL received: %s" % (__plugin__, data), xbmc.LOGDEBUG)

                    # test if link is video or need to be resolved
                    link = ""
                    ext = re.search(__regex__, data)
                    if ext and ext.group(0) in __mediaext__:
                        link = data
                    elif "crunchyroll.com" in data:
                        # special crunchyroll handler, requires crunchyroll-takeout plugin to be installed
                        xbmc.executeJSONRPC('{"jsonrpc":"2.0", "id":1, "method":"Player.Open", "params":{"item":{"file":"plugin://plugin.video.crunchyroll-takeout/?url=' + data + '"}}}')
                        sendtoclient(connection, browser, "1")
                        continue
                    elif "akibapass.de" in data:
                        # special akibapass handler, requires akibapass plugin to be installed
                        xbmc.executeJSONRPC('{"jsonrpc":"2.0", "id":1, "method":"Player.Open", "params":{"item":{"file":"plugin://plugin.video.akibapass/?url=' + data + '"}}}')
                        sendtoclient(connection, browser, "1")
                        continue
                    elif "wakanim.tv" in data:
                        # special wakanim handler, requires wakanim plugin to be installed
                        xbmc.executeJSONRPC('{"jsonrpc":"2.0", "id":1, "method":"Player.Open", "params":{"item":{"file":"plugin://plugin.video.wakanim/?url=' + data + '"}}}')
                        sendtoclient(connection, browser, "1")
                        continue
                    elif data:
                        try:
                            if urlresolverimport:
                                link = urlresolver.resolve(data)
                        except:
                            pass

                    if link:
                        if xbmc.Player().isPlaying():
                            # add to playlist
                            sendtoclient(connection, browser, "2")
                            playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
                            playlist.add(link)
                        else:
                            # play
                            sendtoclient(connection, browser, "1")
                            playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
                            playlist.clear()
                            playlist.add(link)
                            xbmc.Player().play(playlist)
                    else:
                        # unable to play
                        sendtoclient(connection, browser, "0")
                        xbmc.log("[SERVICE] %s: The received URL could not be played" % __plugin__, xbmc.LOGDEBUG)
                        xbmcgui.Dialog().notification(__plugin__, __settings__.getLocalizedString(30102), xbmcgui.NOTIFICATION_WARNING)

            finally:
                # close connection
                connection.close()

        except socket.error:
            # continue if no connection
            continue


    # shut down service
    xbmc.log("[SERVICE] %s: The service will be shut down" % __plugin__, xbmc.LOGDEBUG)
    sock.close()

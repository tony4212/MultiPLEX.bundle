# XMLTV files parser for Plex IPTV plug-in that plays live streams (like IPTV) from a M3U playlist

# Copyright © 2013-2017 Valdas Vaitiekaitis

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

import urllib2
import io
import gzip
import xml.etree.ElementTree # Plex XML API fails with big files

####################################################################################################
def LoadGuide():

    channels = {}
    guide = {}
    xmltv_files = Prefs['xmltv'].split(';')

    for xmltv_file in xmltv_files:
        if xmltv_file:
            if xmltv_file.startswith('http://') or xmltv_file.startswith('https://'):
                # Plex can't handle compressed files, using standart Python methods instead
                if xmltv_file.endswith('.gz') or xmltv_file.endswith('.gz?raw=1'):
                    f = io.BytesIO(urllib2.urlopen(xmltv_file).read())
                    try:
                        g = gzip.GzipFile(fileobj = f)
                        xmltv = g.read()
                    except:
                        Log.Error('Provided file %s is not a valid GZIP file' % xmltv_file)
                        xmltv = None
                else:
                    xmltv = HTTP.Request(xmltv_file).content
            else:
                # Local compressed files are not supported at the moment
                xmltv = Resource.Load(xmltv_file, binary = True)

            if xmltv:
                try:
                    #root = XML.ElementFromString(xmltv, encoding = None)
                    root = xml.etree.ElementTree.fromstring(xmltv)
                except:
                    Log.Error('Provided file %s is not a valid XML file' % xmltv_file)
                    root = None
                if root:
                    for channel in root.findall('./channel'):
                        id = channel.get('id')
                        if id:
                            for name in channel.findall('display-name'):
                                key = unicode(name.text)
                                if key:
                                    channels[key] = id
                    count = 0
                    current_datetime = Datetime.Now()
                    for programme in root.findall('./programme'):
                        channel = unicode(programme.get('channel'))
                        start = StringToLocalDatetime(programme.get('start'))
                        stop = StringToLocalDatetime(programme.get('stop'))
                        if stop >= current_datetime:
                            title = programme.find('title').text
                            desc_node = programme.find('desc')
                            try:
                                desc = unicode(programme.find('desc').text)
                            except:
                                desc = None
                            count = count + 1
                            item = {
                                'start': start,
                                'stop': stop,
                                'title': title,
                                'desc': desc,
                                'order': count
                            }
                            guide.setdefault(channel, {})[count] = item

    Dict['channels'] = channels
    Dict['guide'] = guide
    Dict['last_guide_load_datetime'] = Datetime.Now()
    Dict['last_guide_load_prefs'] = Prefs['xmltv']

####################################################################################################
def StringToLocalDatetime(arg_string):

    arg_string_split = arg_string.split(' ')
    arg_datetime = Datetime.ParseDate(arg_string_split[0])
    if len(arg_string_split) > 1:
        arg_offset_str = arg_string_split[1]
        arg_offset_hours = int(arg_offset_str[0:3])
        arg_offset_minutes = int(arg_offset_str[3:5])
        arg_offset_seconds = (arg_offset_hours * 60 * 60) + (arg_offset_minutes * 60)
        utc_datetime = arg_datetime - Datetime.Delta(seconds = arg_offset_seconds)
    else:
        utc_datetime = arg_datetime
    loc_offset_seconds = (Datetime.Now() - Datetime.UTCNow()).total_seconds()
    loc_datetime = utc_datetime + Datetime.Delta(seconds = loc_offset_seconds)
    return loc_datetime

####################################################################################################
def GuideReloader():

    while True:
        if Prefs['xmltv']:
            if Prefs['xmltv'] != Dict['last_guide_load_prefs'] or not Dict['last_guide_load_datetime']:
                LoadGuide()
            elif Prefs['xmltv_reload_time'] != 'never':
                current_datetime = Datetime.Now()
                next_load_datetime = Datetime.ParseDate(str(current_datetime.date()) + ' ' + Prefs['xmltv_reload_time'] + ':00')
                if current_datetime > next_load_datetime and next_load_datetime > Dict['last_guide_load_datetime']:
                    LoadGuide()
        Thread.Sleep(10)
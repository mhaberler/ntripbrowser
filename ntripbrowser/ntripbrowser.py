# ntripbrowser code is placed under the GPL license.
# Written by Ivan Sapozhkov (ivan.sapozhkov@emlid.com)
# Copyright (c) 2016, Emlid Limited
# All rights reserved.

# If you are interested in using ntripbrowser code as a part of a
# closed source project, please contact Emlid Limited (info@emlid.com).

# This file is part of ntripbrowser.

# ntripbrowser is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# ntripbrowser is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with ntripbrowser.  If not, see <http://www.gnu.org/licenses/>.
# from __future__ import unicode_literals

import urllib2
import httplib
import argparse
import chardet
from geopy.distance import vincenty

def argparser():
    parser = argparse.ArgumentParser(description='Parse NTRIP sourcetable')
    parser.add_argument("url", help="NTRIP sourcetable address")
    parser.add_argument("-p", "--port", type=int,
                        help="change url port. Standart port is 2101", default=2101)
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="increase output verbosity")
    parser.add_argument("-N", "--NETtable", action="store_true",
                        help="additional show NET table")
    parser.add_argument("-C", "--CATtable", action="store_true",
                        help="additional show CAT table")
    parser.add_argument("-n", "--no-pager", action="store_true",
                        help="no pager")
    parser.add_argument("-s", "--source", action="store_true",
                        help="display url source data")
    parser.add_argument("-t", "--timeout", type=int,
                        help="add timeout", default=None)
    parser.add_argument("-b", "--BasePointCoord",
                        help="add base point coordiantes x,y")
    return parser.parse_args()

def read_url(url, timeout):
    ntrip_request = urllib2.urlopen(url, timeout=timeout)
    ntrip_table_raw = ntrip_request.read()
    ntrip_request.close()
    return ntrip_table_raw

def decode_text(text):
    detected_table_encoding = chardet.detect(text)['encoding']
    return text.decode(detected_table_encoding)

def crop_sourcetable(sourcetable):
    CAS = sourcetable.find('\n'+'CAS')
    NET = sourcetable.find('\n'+'NET')
    STR = sourcetable.find('\n'+'STR')
    first = CAS if (CAS != -1) else (NET if NET != -1 else STR)
    last = sourcetable.find('ENDSOURCETABLE')
    return sourcetable[first:last]

def parse_ntrip_table(raw_text):
    raw_table = crop_sourcetable(raw_text)
    ntrip_tables = extract_ntrip_entry_strings(raw_table)
    return ntrip_tables

def extract_ntrip_entries(raw_table):
    str_list, cas_list, net_list = extract_ntrip_entry_strings(raw_table)
    return form_ntrip_entries(str_list, cas_list, net_list)

def extract_ntrip_entry_strings(raw_table):
    str_list, cas_list, net_list = [], [], []
    for row in raw_table.split("\n"):
        if row.startswith("STR"):
            str_list.append(row)
        elif row.startswith("CAS"):
            cas_list.append(row)
        elif row.startswith("NET"):
            net_list.append(row)
    return str_list, cas_list, net_list

def form_ntrip_entries(ntrip_tables):
    return {
        "str": form_str_dictionary(ntrip_tables[0]),
        "cas": form_cas_dictionary(ntrip_tables[1]),
        "net": form_net_dictionary(ntrip_tables[2])
    }

def form_str_dictionary(str_list):
    STR_headers = ["Mountpoint","ID","Format","Format-Details",
        "Carrier","Nav-System","Network","Country","Latitude",
        "Longitude","NMEA","Solution","Generator","Compr-Encrp",
        "Authentication","Fee","Bitrate","Other Details"]
    return form_dictionaries(STR_headers, str_list)

def form_cas_dictionary(cas_list):
    CAS_headers = ["Host","Port","ID","Operator",
        "NMEA","Country","Latitude","Longitude",
        "Fallback\nHost","Fallback\nPort","Site"]
    return form_dictionaries(CAS_headers, cas_list)

def form_net_dictionary(net_list):
    NET_headers = ["ID","Operator","Authentication",
        "Fee","Web-Net","Web-Str","Web-Reg",""]
    return form_dictionaries(NET_headers, net_list)

def form_dictionaries(headers, line_list):
    dict_list = []
    for i in line_list:
        line_dict = i.split(";", len(headers))[1:]
        info = dict(zip(headers, line_dict))
        dict_list.append(info)
    return dict_list

def get_distance(obs_point, base_point):
    return vincenty(obs_point, base_point).kilometers

def add_distance_row(ntrip_type_dictionary, base_point):
    for station in ntrip_type_dictionary:
        dictionary_latlon = (station.get('Latitude'), station.get('Longitude'))
        distance = get_distance(dictionary_latlon, base_point)
        station['Distance'] = distance
    return ntrip_type_dictionary

def station_distance(ntrip_dictionary, base_point):
    return {
        "cas": add_distance_row(ntrip_dictionary.get('cas'), base_point),
        "net": add_distance_row(ntrip_dictionary.get('net'), base_point),
        "str": add_distance_row(ntrip_dictionary.get('str'), base_point)
    }

def main():
    args = argparser()
    NTRIP_url = None
    if (args.url.find("http") != -1):
        pream = ''
    else:
        pream = 'http://'
    ntrip_url = '{}{}:{}'.format(pream, args.url, args.port)
    print(ntrip_url)

    try:
        ntrip_table_raw = read_url(ntrip_url, timeout=args.timeout)
    except (IOError, httplib.HTTPException):
        print("Bad url")
        pass
    else:
        ntrip_table_raw_decoded = decode_text(ntrip_table_raw)
        ntrip_tables = parse_ntrip_table(ntrip_table_raw_decoded)
        ntrip_dictionary = form_ntrip_entries(ntrip_tables)
        station_dict = station_distance(ntrip_dictionary, base_point = (args.BasePointCoord))
        print station_dict

if __name__ == '__main__':
    main()
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# encoding=utf8
# Copyright (c) 2017 @x0rz
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# Usage:
# python tweets_analyzer.py -n screen_name
#
# Install:
# pip install tweepy ascii_graph tqdm numpy

from __future__ import unicode_literals
from ascii_graph import Pyasciigraph
from ascii_graph.colors import Gre, Yel, Red
from ascii_graph.colordata import hcolor
from tqdm import tqdm
import tweepy
import numpy
import argparse
import collections
import datetime
import time
import sys
import copy
import os
from urlparse import urlparse
from secrets import consumer_key, consumer_secret, access_token, access_token_secret
import pydot 
import pickle

__version__ = '0.3'

def set_output_encoding(encoding='utf-8'):
    """ 
    Needed to have good encoding when piping into other program
    """
    import sys
    import codecs
    '''When piping to the terminal, python knows the encoding needed, and
       sets it automatically. But when piping to another program (for example,
       | less), python can not check the output encoding. In that case, it 
       is None. What I am doing here is to catch this situation for both 
       stdout and stderr and force the encoding'''
    current = sys.stdout.encoding
    if current is None :
        sys.stdout = codecs.getwriter(encoding)(sys.stdout)
    current = sys.stderr.encoding
    if current is None :
        sys.stderr = codecs.getwriter(encoding)(sys.stderr)

class User():
    """ 
    A class to manage all the data of a twitter user
    """
    def __init__(self, screen_name):
        self.screen_name = screen_name
        self.creation_time = datetime.datetime.now()
        self.tweets = {}
        self.detected_langs = collections.Counter()
        self.detected_sources = collections.Counter()
        self.detected_places = collections.Counter()
        self.geo_enabled_tweets = 0
        self.detected_hashtags = collections.Counter()
        self.detected_domains = collections.Counter()
        self.detected_timezones = collections.Counter()
        self.retweets = 0
        self.retweeted_users = collections.Counter()
        self.mentioned_users = collections.Counter()
        self.id_screen_names = {}
        self.friends_timezone = collections.Counter()
        self.friends_lang = collections.Counter()
        self.friends = {}
        self.dirpath = ''
        self.last_friend_retrieved_id = False
        self.user_info = False

    def set_twitter_info(self, data):
        """ To call if you first obtained the data from twitter, you created a user and now you want to store it """
        #self.user_info = copy.deepcopy(data)
        self.user_info = data

    def get_twitter_info(self):
        """ To call if you created this user only with a name, and want more data """
        try:
            self.user_info = twitter_api.get_user(self.screen_name)
        except tweepy.error.TweepError as e:
            print('This user is protected and we can not get its data.')

    def get_tweets(self, api, username, limit):
        """ Download Tweets from username account """
        for status in tqdm(tweepy.Cursor(api.user_timeline, screen_name=username).items(limit),
                           unit="tw", total=limit):
            process_tweet(status)

    def print_summary(self, color):
        if color:
            def bold(text):
                return '\033[1m' + text + '\033[0m'
        else:
            def bold(text):
                return text
        print('[+] User           : {}'.format(bold('@'+self.screen_name)))
        print('[+] Date:          : {}'.format(bold(str(self.creation_time))))
        print('[+] lang           : {}'.format(bold(self.user_info.lang)))
        print('[+] geo_enabled    : {}'.format(bold(str(self.user_info.geo_enabled))))
        print('[+] time_zone      : {}'.format(bold(str(self.user_info.time_zone))))
        print('[+] utc_offset     : {}'.format(bold(str(self.user_info.utc_offset))))
        print('[+] Followers      : {}'.format(bold(str(self.user_info.followers_count))))
        print('[+] Friends        : {}'.format(bold(str(self.user_info.friends_count))))
        print('[+] Friends cache  : {}'.format(bold(str(len(self.friends)))))
        print('[+] MemberPubLits  : {}'.format(bold(str(self.user_info.listed_count))))
        print('[+] Location       : {}'.format(bold(self.user_info.location)))
        print('[+] Name           : {}'.format(bold(self.user_info.name)))
        print('[+] Protected      : {}'.format(bold(str(self.user_info.protected))))
        print('[+] Screen Name    : {}'.format(bold(self.screen_name)))
        print('[+] # Tweets       : {}'.format(bold(str(self.user_info.statuses_count))))
        print('[+] URL            : {}'.format(bold(str(self.user_info.url))))
        print('[+] Verified?      : {}'.format(bold(str(self.user_info.verified))))
        print('[+] Tweets liked   : {}'.format(bold(str(self.user_info.favourites_count))))
        print('')

    def print_followers(self):
        """ 
        Print only the info about followers
        """
        print('{},{},{}'.format(self.creation_time,self.screen_name,self.user_info.followers_count))

    def analyze_friends(self, numfriends, offline):
        """
        Analyze the friends of this user
        numfriends: Max num of friends to retrieve
        offline: if we use offline friends
        """
        max_friends = numpy.amin([self.user_info.friends_count, numfriends])
        print('[+] Analyzing friends.')
        self.process_friends()
        print("[+] Friends languages")
        print_stats(self.friends_lang, top=10)
        print("[+] Friends timezones")
        print_stats(self.friends_timezone, top=10)

    def get_friends(self, api, username, limit, offline):
        """
        Get friends. Load friends from cache
        If offline, do not retrieve from twitter 
        If online and we have in the cache less than the limit, continue downloading from the last friend downloaded
        """
        # Load the cache of friends. Always
        if args.debug > 0:
            print('Loading the cache of friends...')
        try:
            friends = pickle.load( open( self.dirpath + self.screen_name + '/' + self.screen_name + '.twitter_friends', "rb" ) )
            for friend in friends.values():
                UserFriend = User(friend.screen_name)
                UserFriend.set_twitter_info(friend.user_info)
                self.friends[friend.screen_name] = UserFriend
        except IOError:
            print('This user does not have a cache of friends yet.')
        # Are we offline?
        if args.debug > 0 and offline:
            print('We are in offline mode, so we are not downloading more friends.')
        #elif not offline and (limit == -1 or limit > len(self.friends)):
        elif not offline:
            # Get the list of friends
            try:
                self.friends_ids = twitter_api.friends_ids(self.screen_name)
            except tweepy.error.TweepError as e:
                print('This user is protected and we can not get its data.')
                return False
            print('Total amount of friends this user follows: {}'.format(self.user_info.friends_count))
            print('Total amount of friends downloaded in cache: {}'.format(len(self.friends)))
            # If the limit requested is > than the amount we already have, continue downloading from where we left
            if self.last_friend_retrieved_id and self.last_friend_retrieved_id != self.friends_ids[-1]:
                if args.debug > 0:
                    print('We didn\'t finished downloading the list of friends. Continuing...')
                friends_to_continue_download = self.friends_ids[self.friends_ids.index(self.last_friend_retrieved_id):]
            else:
                friends_to_continue_download = self.friends_ids
            friends_to_download = friends_to_continue_download[:limit]
            print('Friends to download: {}'.format(len(friends_to_download)))
            # We split the friends in groups in case we need to sleep because we are asking to much. Now not so used because we wait for the twitter exception
            group_size = 20
            splitted_friends = [friends_to_download[x:x+group_size] for x in range(0, len(friends_to_download), group_size) ]
            amount_groups = 0
            amount_users = 0
            for splitted_group in splitted_friends:
                for friend_id in splitted_group:
                        try:
                            if args.debug > 0:
                                print('Downloading friend Nr {}: {}'.format(amount_users, friend_id))
                            try:
                                friend = twitter_api.get_user(friend_id)
                            except tweepy.error.TweepError as e:
                                if e[0][0]['code'] == 88 or e[0][0]['code'] == 50:
                                    print("Rate limit exceeded to get friends data, we will sleep are retry in 15 minutes. The friends so far are stored.")
                                # Store friends so far
                                #pickle.dump(self.friends, friends_file_fd )
                                pickle.dump(self.friends, open( self.dirpath + self.screen_name + '/' + self.screen_name + '.twitter_friends', "wb" ) )
                                # Sleep
                                print('Waiting 15 minutes...')
                                time.sleep(900)
                                print('Resuming download...')
                                # Retrieve the same last user that we couldn't before
                                friend = twitter_api.get_user(friend_id)
                                continue
                            except Exception as e:
                                # catch all? What are we doing here?
                                print('Weird catch. Error {}'.format(e))
                                print('Save friends.')
                                #pickle.dump(self.friends, friends_file_fd )
                                pickle.dump(self.friends, open( self.dirpath + self.screen_name + '/' + self.screen_name + '.twitter_friends', "wb" ) )
                            UserFriend = User(friend.screen_name)
                            UserFriend.set_twitter_info(friend)
                            self.friends[friend.screen_name] = UserFriend
                            self.last_friend_retrieved_id = UserFriend.user_info.id
                            amount_users += 1
                        except KeyboardInterrupt:
                            # Print Summary of detections in the last Time Window
                            print('Keyboard Interrupt. Storing the friends')
                            #pickle.dump(self.friends, friends_file_fd )
                            pickle.dump(self.friends, open( self.dirpath + self.screen_name + '/' + self.screen_name + '.twitter_friends', "wb" ) )
                            raise
                # Between groups save friends
                #pickle.dump(self.friends, friends_file_fd )
                pickle.dump(self.friends, open( self.dirpath + self.screen_name + '/' + self.screen_name + '.twitter_friends', "wb" ) )
                amount_groups += 1
            # Store the friends at the end
            #pickle.dump(self.friends, friends_file_fd )
            pickle.dump(self.friends, open( self.dirpath + self.screen_name + '/' + self.screen_name + '.twitter_friends', "wb" ) )
        # Finally continue processing the friends

    def process_friends(self):
        """ Process all the friends """
        for friend in self.friends:
            try:
                if self.friends[friend].user_info.lang:
                    self.friends_lang[self.friends[friend].user_info.lang] += 1
                if self.friends[friend].user_info.time_zone:
                    self.friends_timezone[self.friends[friend].user_info.time_zone] += 1
            except AttributeError:
                if args.debug > 2:
                    print('Processing Friend {}'.format(friend))
                    print 'The friend does not have data!'

class Tweet():
    """
    A class for storing tweet data
    """
    def __init__():
        self.date = None

activity_hourly = {
    ("%2i:00" % i).replace(" ", "0"): 0 for i in range(24)
}

activity_weekly = {
    "%i" % i: 0 for i in range(7)
}



def process_tweet(tweet):
    """ Processing a single Tweet and updating our datasets """
    global geo_enabled_tweets
    global retweets

    # Check for filters before processing any further
    if args.filter and tweet.source:
        if not args.filter.lower() in tweet.source.lower():
            return

    tw_date = tweet.created_at

    # Handling retweets
    try:
        # We use id to get unique accounts (screen_name can be changed)
        rt_id_user = tweet.retweeted_status.user.id_str
        retweeted_users[rt_id_user] += 1

        if tweet.retweeted_status.user.screen_name not in id_screen_names:
            id_screen_names[rt_id_user] = "@%s" % tweet.retweeted_status.user.screen_name

        retweets += 1
    except:
        pass

    # Adding timezone from profile offset to set to local hours
    if tweet.user.utc_offset and not args.no_timezone:
        tw_date = (tweet.created_at + datetime.timedelta(seconds=tweet.user.utc_offset))

    if args.utc_offset:
        tw_date = (tweet.created_at + datetime.timedelta(seconds=args.utc_offset))

    # Updating our activity datasets (distribution maps)
    activity_hourly["%s:00" % str(tw_date.hour).zfill(2)] += 1
    activity_weekly[str(tw_date.weekday())] += 1

    # Updating langs
    detected_langs[tweet.lang] += 1

    # Updating sources
    detected_sources[tweet.source] += 1

    # Detecting geolocation
    if tweet.place:
        geo_enabled_tweets += 1
        tweet.place.name = tweet.place.name
        detected_places[tweet.place.name] += 1

    # Updating hashtags list
    if tweet.entities['hashtags']:
        for ht in tweet.entities['hashtags']:
            ht['text'] = "#%s" % ht['text']
            detected_hashtags[ht['text']] += 1

    # Updating domains list
    if tweet.entities['urls']:
        for url in tweet.entities['urls']:
            domain = urlparse(url['expanded_url']).netloc
            if domain != "twitter.com":  # removing twitter.com from domains (not very relevant)
                detected_domains[domain] += 1

    # Updating mentioned users list
    if tweet.entities['user_mentions']:
        for ht in tweet.entities['user_mentions']:
            mentioned_users[ht['id_str']] += 1
            if not ht['screen_name'] in id_screen_names:
                id_screen_names[ht['id_str']] = "@%s" % ht['screen_name']

def print_stats(dataset, top=5):
    """ Displays top values by order """
    sum = numpy.sum(list(dataset.values()))
    i = 0
    if sum:
        sorted_keys = sorted(dataset, key=dataset.get, reverse=True)
        max_len_key = max([len(x) for x in sorted_keys][:top])  # use to adjust column width
        for k in sorted_keys:
            try:
                print(("- \033[1m{:<%d}\033[0m {:>6} {:<4}" % max_len_key)
                      .format(k, dataset[k], "(%d%%)" % ((float(dataset[k]) / sum) * 100)))
            except:
                import ipdb
                ipdb.set_trace()
            i += 1
            if i >= top:
                break
    else:
        print("No data")
    print("")


def print_charts(dataset, title, weekday=False):
    """ Prints nice charts based on a dict {(key, value), ...} """
    chart = []
    keys = sorted(dataset.keys())
    mean = numpy.mean(list(dataset.values()))
    median = numpy.median(list(dataset.values()))

    def int_to_weekday(day):
        weekdays = "Monday Tuesday Wednesday Thursday Friday Saturday Sunday".split()
        return weekdays[int(day) % len(weekdays)]

    for key in keys:
        if (dataset[key] >= median * 1.33):
            displayed_key = "%s (\033[92m+\033[0m)" % (int_to_weekday(key) if weekday else key)
        elif (dataset[key] <= median * 0.66):
            displayed_key = "%s (\033[91m-\033[0m)" % (int_to_weekday(key) if weekday else key)
        else:
            displayed_key = (int_to_weekday(key) if weekday else key)

        chart.append((displayed_key, dataset[key]))

    thresholds = {
        int(mean): Gre, int(mean * 2): Yel, int(mean * 3): Red,
    }
    data = hcolor(chart, thresholds)

    graph = Pyasciigraph(
        separator_length=4,
        multivalue=False,
        human_readable='si',
    )

    for line in graph.graph(title, data):
        print('{}'.format(line))
    print("")


def main():

    return True

    # Get specific data
    try:
        censored = user_info.withheld_in_countries
    except Exception as e:
        censored = 'None'
    print("[+] Censored in countries : \033[1m%s\033[0m" % censored)

    if user_info.utc_offset is None:
        print("[\033[91m!\033[0m] Can't get specific timezone for this user")

    if args.utc_offset:
        print("[\033[91m!\033[0m] Applying timezone offset %d (--utc-offset)" % args.utc_offset)

    if args.summary:
        return True

    # Will retreive all Tweets from account (or max limit)
    num_tweets = numpy.amin([args.limit, user_info.statuses_count])
    print("[+] Retrieving last %d tweets..." % num_tweets)

    # Download tweets
    get_tweets(twitter_api, args.name, limit=num_tweets)
    print("[+] Downloaded %d tweets" % (num_tweets))

    # Checking if we have enough data (considering it's good to have at least 30 days of data)

    # Print activity distrubution charts
    print_charts(activity_hourly, "Daily activity distribution (per hour)")
    print_charts(activity_weekly, "Weekly activity distribution (per day)", weekday=True)

    print("[+] Detected languages (top 5)")
    print_stats(detected_langs)

    print("[+] Detected sources (top 10)")
    print_stats(detected_sources, top=10)

    print("[+] There are \033[1m%d\033[0m geo enabled tweet(s)" % geo_enabled_tweets)
    if len(detected_places) != 0:
        print("[+] Detected places (top 10)")
        print_stats(detected_places, top=10)

    print("[+] Top 10 hashtags")
    print_stats(detected_hashtags, top=10)

    if num_tweets > 0:
        print("[+] @%s did \033[1m%d\033[0m RTs out of %d tweets (%.1f%%)" % (args.name, retweets, num_tweets, (float(retweets) * 100 / num_tweets)))

    # Converting users id to screen_names
    retweeted_users_names = {}
    for k in retweeted_users.keys():
        retweeted_users_names[id_screen_names[k]] = retweeted_users[k]

    print("[+] Top 5 most retweeted users")
    print_stats(retweeted_users_names, top=5)

    mentioned_users_names = {}
    for k in mentioned_users.keys():
        mentioned_users_names[id_screen_names[k]] = mentioned_users[k]
    print("[+] Top 5 most mentioned users")
    print_stats(mentioned_users_names, top=5)

    print("[+] Most referenced domains (from URLs)")
    print_stats(detected_domains, top=6)


def plot_users(users, dirpath):
    """ Read the friends of these users from a file and plot a graph"""
    print('Plotting a unique graph for all users')
    pygraph = pydot.Dot(graph_type='graph', resolution='76800')
    pygraph.set('center', '1')
    pygraph.set('ratio', 'auto')
    pygraph.set_fontsize('21')
    pygraph.set_ranksep('3 equally')
    pygraph.set_rankdir('LR')
    #pygraph.set_rank('sink')
    #print(pygraph.get_resolution())
    counter_papa = {}
    j=0
    for user in users.split(','):
        # read their friends
        node = pydot.Node(user,fontcolor='black',shape='rectangle')
        node.set_group('First')
        pygraph.add_node(node)
        try:
            friends = pickle.load( open( dirpath + '/' + user + '/' + user + '.twitter_friends', "rb" ) )
        except IOError:
            # This user is not in the cache
            continue
        for friend in list(set(friends.values())):
            node = pydot.Node(friend.screen_name,fontcolor='black')
            node.set_group('Second')
            pygraph.add_node(node)
            # Make an edge
            edge = pydot.Edge(user, friend.screen_name)
            pygraph.add_edge(edge)
            try:
                counter_papa[friend.screen_name] += 1
            except KeyError:
                counter_papa[friend.screen_name] = 1
            j += 1
        print('{} nodes added for user {}'.format(j, user))
        j=0
    nodes = pygraph.get_node_list()
    i=0
    for node in counter_papa:
        if counter_papa[node] == 1:
            counter_papa[node] = 'LightBlue'
        elif counter_papa[node] == 2:
            counter_papa[node] = 'Red'
        elif counter_papa[node] == 3:
            counter_papa[node] = 'Yellow'
        elif counter_papa[node] == 4:
            counter_papa[node] = 'Blue'
        elif counter_papa[node] == 5:
            counter_papa[node] = 'Orange'
        elif counter_papa[node] == 6:
            counter_papa[node] = 'crimson'
        elif counter_papa[node] == 7:
            counter_papa[node] = 'forestgreen'
        elif counter_papa[node] == 8:
            counter_papa[node] = 'deeppink'
        elif counter_papa[node] == 9:
            counter_papa[node] = 'cadetblue'
        elif counter_papa[node] == 10:
            counter_papa[node] = 'aquamarine'
    for node in nodes:
        if node.get_group() == 'Second':
            #print('{}: {}'.format(node.get_name(), node.get_root()))
            node.set_style('filled')
            try:
                node.set_fillcolor(counter_papa[node.get_name()])
            except KeyError:
                pass
            i += 1
        elif node.get_group() == 'First':
            #print(node.get_name())
            node.set_fontsize('36')
            node.set_color('red')
            node.set_fontname('Times-Bold')
            node.set_fontcolor('yellow')
            node.set_fillcolor('black')
            node.set_style('filled')
    print('{} nodes reviewed'.format(i))
    #pygraph.write_png('{}.graph.png'.format(users))
    pygraph.write_png('graph.png')
    # Node methods
    # 'add_style', 'create_attribute_methods', 'get', 'get_URL', 'get_attributes', 
    # 'get_color', 'get_colorscheme', 'get_comment', 'get_distortion', 'get_fillcolor', 
    # 'get_fixedsize', 'get_fontcolor', 'get_fontname', 'get_fontsize', 'get_group', 'get_height', 
    # 'get_id', 'get_image', 'get_imagescale', 'get_label', 'get_labelloc', 'get_layer', 
    # 'get_margin', 'get_name', 'get_nojustify', 'get_orientation', 'get_parent_graph', 'get_penwidth', 
    # 'get_peripheries', 'get_pin', 'get_port', 'get_pos', 'get_rects', 'get_regular', 'get_root', 
    # 'get_samplepoints', 'get_sequence', 'get_shape', 'get_shapefile', 'get_showboxes', 'get_sides', 
    # 'get_skew', 'get_sortv', 'get_style', 'get_target', 'get_texlbl', 'get_texmode', 'get_tooltip', 
    # 'get_vertices', 'get_width', 'get_z', 'obj_dict', 'set', 'set_URL', 'set_color', 'set_colorscheme', 
    # 'set_comment', 'set_distortion', 'set_fillcolor', 'set_fixedsize', 'set_fontcolor', 'set_fontname', 
    # 'set_fontsize', 'set_group', 'set_height', 'set_id', 'set_image', 'set_imagescale', 'set_label', 
    # 'set_labelloc', 'set_layer', 'set_margin', 'set_name', 'set_nojustify', 'set_orientation', 
    # 'set_parent_graph', 'set_penwidth', 'set_peripheries', 'set_pin', 'set_pos', 'set_rects', 
    # 'set_regular', 'set_root', 'set_samplepoints', 'set_sequence', 'set_shape', 'set_shapefile', 'set_showboxes', 
    # 'set_sides', 'set_skew', 'set_sortv', 'set_style', 'set_target', 'set_texlbl', 'set_texmode', 
    # 'set_tooltip', 'set_vertices', 'set_width', 'set_z', 'to_string']

    # Graph methods
    #pygraph.write_dot('{}.graph.xdot'.format(users))
    # 'add_edge', 'add_node', 'add_subgraph', 'create', 'create_attribute_methods', 
    # 'create_canon', 'create_cmap', 'create_cmapx', 'create_cmapx_np', 'create_dia', 
    # 'create_dot', 'create_fig', 'create_gd', 'create_gd2', 'create_gif', 'create_hpgl', 
    # 'create_imap', 'create_imap_np', 'create_ismap', 'create_jpe', 'create_jpeg', 
    # 'create_jpg', 'create_mif', 'create_mp', 'create_pcl', 'create_pdf', 'create_pic', 
    # 'create_plain', 'create_plain-ext', 'create_png', 'create_ps', 'create_ps2', 'create_svg', 
    # 'create_svgz', 'create_vml', 'create_vmlz', 'create_vrml', 'create_vtx', 'create_wbmp', 
    # 'create_xdot', 'create_xlib', 'del_edge', 'del_node', 'formats', 'get', 'get_Damping', 
    # 'get_K', 'get_URL', 'get_aspect', 'get_attributes', 'get_bb', 'get_bgcolor', 
    # 'get_center', 'get_charset', 'get_clusterrank', 'get_colorscheme', 'get_comment', 
    # 'get_compound', 'get_concentrate', 'get_defaultdist', 'get_dim', 'get_dimen', 
    # 'get_diredgeconstraints', 'get_dpi', 'get_edge', 'get_edge_defaults', 'get_edge_list', 
    # 'get_edges', 'get_epsilon', 'get_esep', 'get_fontcolor', 'get_fontname', 'get_fontnames', 
    # 'get_fontpath', 'get_fontsize', 'get_graph_defaults', 'get_graph_type', 'get_id', 'get_label', 
    # 'get_labeljust', 'get_labelloc', 'get_landscape', 'get_layers', 'get_layersep', 'get_layout', 
    # 'get_levels', 'get_levelsgap', 'get_lheight', 'get_lp', 'get_lwidth', 'get_margin', 'get_maxiter', 
    # 'get_mclimit', 'get_mindist', 'get_mode', 'get_model', 'get_mosek', 'get_name', 'get_next_sequence_number', 
    # 'get_node', 'get_node_defaults', 'get_node_list', 'get_nodes', 'get_nodesep', 'get_nojustify', 
    # 'get_normalize', 'get_nslimit', 'get_nslimit1', 'get_ordering', 'get_orientation', 'get_outputorder', 
    # 'get_overlap', 'get_overlap_scaling', 'get_pack', 'get_packmode', 'get_pad', 'get_page', 
    # 'get_pagedir', 'get_parent_graph', 'get_quadtree', 'get_quantum', 'get_rank', 'get_rankdir', 
    # 'get_ranksep', 'get_ratio', 'get_remincross', 'get_repulsiveforce', 'get_resolution', 
    # 'get_root', 'get_rotate', 'get_searchsize', 'get_sep', 'get_sequence', 'get_showboxes', 
    # 'get_simplify', 'get_size', 'get_smoothing', 'get_sortv', 'get_splines', 'get_start', 
    # 'get_strict', 'get_stylesheet', 'get_subgraph', 'get_subgraph_list', 'get_subgraphs', 
    # 'get_suppress_disconnected', 'get_target', 'get_top_graph_type', 'get_truecolor', 
    # 'get_type', 'get_viewport', 'get_voro_margin', 'obj_dict', 'prog', 'set', 'set_Damping', 
    # 'set_K', 'set_URL', 'set_aspect', 'set_bb', 'set_bgcolor', 'set_center', 'set_charset', 
    # 'set_clusterrank', 'set_colorscheme', 'set_comment', 'set_compound', 'set_concentrate', 
    # 'set_defaultdist', 'set_dim', 'set_dimen', 'set_diredgeconstraints', 'set_dpi', 'set_edge_defaults', 
    # 'set_epsilon', 'set_esep', 'set_fontcolor', 'set_fontname', 'set_fontnames', 'set_fontpath', 
    # 'set_fontsize', 'set_graph_defaults', 'set_id', 'set_label', 'set_labeljust', 'set_labelloc', 
    # 'set_landscape', 'set_layers', 'set_layersep', 'set_layout', 'set_levels', 'set_levelsgap', 
    # 'set_lheight', 'set_lp', 'set_lwidth', 'set_margin', 'set_maxiter', 'set_mclimit', 'set_mindist', 
    # 'set_mode', 'set_model', 'set_mosek', 'set_name', 'set_node_defaults', 'set_nodesep', 'set_nojustify', 
    # 'set_normalize', 'set_nslimit', 'set_nslimit1', 'set_ordering', 'set_orientation', 'set_outputorder', 
    # 'set_overlap', 'set_overlap_scaling', 'set_pack', 'set_packmode', 'set_pad', 'set_page', 
    # 'set_pagedir', 'set_parent_graph', 'set_prog', 'set_quadtree', 'set_quantum', 'set_rank', 
    # 'set_rankdir', 'set_ranksep', 'set_ratio', 'set_remincross', 'set_repulsiveforce', 'set_resolution', 
    # 'set_root', 'set_rotate', 'set_searchsize', 'set_sep', 'set_sequence', 'set_shape_files', 
    # 'set_showboxes', 'set_simplify', 'set_size', 'set_smoothing', 'set_sortv', 'set_splines', 
    # 'set_start', 'set_strict', 'set_stylesheet', 'set_suppress_disconnected', 'set_target', 
    # 'set_truecolor', 'set_type', 'set_viewport', 'set_voro_margin', 'shape_files', 
    # 'to_string', 'write', 'write_canon', 'write_cmap', 'write_cmapx', 'write_cmapx_np', 
    # 'write_dia', 'write_dot', 'write_fig', 'write_gd', 'write_gd2', 'write_gif', 'write_hpgl', 
    # 'write_imap', 'write_imap_np', 'write_ismap', 'write_jpe', 'write_jpeg', 'write_jpg', 
    # 'write_mif', 'write_mp', 'write_pcl', 'write_pdf', 'write_pic', 'write_plain', 
    # 'write_plain-ext', 'write_png', 'write_ps', 'write_ps2', 'write_raw', 'write_svg', 
    # 'write_svgz', 'write_vml', 'write_vmlz', 'write_vrml', 'write_vtx', 'write_wbmp', 'write_xdot', 'write_xlib'



if __name__ == '__main__':
    try:
	set_output_encoding()

        # Process Parameters
        parser = argparse.ArgumentParser(description="Simple Twitter Profile Analyzer (https://github.com/x0rz/tweets_analyzer) version %s" % __version__, usage='%(prog)s -n <screen_name> [options]')
        parser.add_argument('-l', '--limit', metavar='N', type=int, default=1000, help='limit the number of tweets to retreive (default=1000)')
        parser.add_argument('-n', '--names', required=False, metavar="screen_names", help='target screen_name. Can be a comma separated list of names for multiple comparisons.')
        parser.add_argument('-f', '--filter', help='filter by source (ex. -f android will get android tweets only)')
        parser.add_argument('--no-timezone', action='store_true', help='removes the timezone auto-adjustment (default is UTC)')
        parser.add_argument('--utc-offset', type=int, help='manually apply a timezone offset (in seconds)')
        parser.add_argument('-r', '--friends', action='store_true', help='Retrieve the friends of each user and perform an analysis on _their_ data. Use -N to select the amount of friends. Use -o if you want to analyze the offline cached friends. (rate limit = 300 friends max, any user, per 15 mins)')
        parser.add_argument('-s', '--nosummary', action='store_true', default=False, help='Do not show the summary of the user.)')
        parser.add_argument('-F', '--quickfollowers', action='store_true', help='Print only a very short summary about the number of followers.')
        parser.add_argument('-c', '--color', action='store_true', help='Use colors when printing')
        parser.add_argument('-N', '--numfriends', action='store', help='Max amount of friends to retrieve when -r is used. Defaults to 200. Use -1 to retrieve all of them. Warning! this can take long, since twitter limits 700 friends requests every 15mins approx.', default=200, type=int)
        parser.add_argument('-g', '--graphusers', action='store_true', help='Get the list of users specified with -n, read their _offline_ list of users, and create a unique graph for all of them and their shared friends..')
        parser.add_argument('-o', '--offline', action='store_true', default=False, help='Use the offline data stored in cache for all the actions. Do not retrieve them from Twitter (use after you retrieved it at least once).')
        parser.add_argument('-L', '--lastfriend', action='store', type=int, help='Last friend we retrieved before, to continue downloading friends after they.')
        parser.add_argument('-d', '--debug', action='store', type=int, default=0, help='Debug level.')
        args = parser.parse_args()

        # The path everyone uses to access the cache
        dirpath = os.path.expanduser('~/.twitter_analyzer_users/')

        # If we want to plot users offline, we don't need even to connect to twitter
        if args.graphusers:
            plot_users(args.names, dirpath)
            sys.exit(0)

        # Connect to Twitter 
        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(access_token, access_token_secret)
        twitter_api = tweepy.API(auth)

        # Go user by user given
        for name in args.names.split(','):
            try:
                # Create our folder if we need it, and the user object
                try:
                    os.makedirs(dirpath + name)
                    print('Folders created in {}'.format(dirpath + name))
                    # The folder Is not there
                    user = User(name)
                except OSError:
                    # Already exists
                    if args.debug > 1:
                        print('The user exists, loading its data.')
                    # Load what we know from this user
                    try:
                        datapath = os.path.expanduser(dirpath + name + '/' + name + '.data')
                        user = pickle.load(open(datapath, 'rb'))
                    except IOError:
                        user = User(name)
                user.dirpath = dirpath
                # Get basic info
                if not args.offline:
                    if args.debug > 1:
                        print('Getting basic twitter info.')
                    user.get_twitter_info()
                # Only show the amount of friends
                if args.quickfollowers:
                    user.print_followers()
                # Print a Summary
                elif not args.nosummary:
                    user.print_summary(args.color)
                    user.analyze_friends(args.numfriends, args.offline)
                # Appart for the rest, do we have x
                if args.friends:
                    user.get_friends(twitter_api, name, args.numfriends, args.offline)
                # Store this user in our disk cache
                pickle.dump(user, open( dirpath + name + '/' + name + '.data', "wb" ) )
            except KeyboardInterrupt:
                # Print Summary of detections in the last Time Window
                print('Keyboard Interrupt. Storing the user')
                pickle.dump(user, open( dirpath + name + '/' + name + '.data', "wb" ) )
        # TODO
        # Finish the summary as before

    except tweepy.error.TweepError as e:
        print("[\033[91m!\033[0m] Twitter error: %s" % e)
        #if e[0][0]['code'] == 88:
            ## rate limit exceded
            #for name in args.names.split(','):
        #pickle.dump(self.friends, open( self.dirpath + '/' + self.screen_name+ '/' + self.screen_name + '.twitter_friends', "wb" ) )
        try:
            if e[0][0]['code'] == 50:
                # user not found
                os.rmdir(dirpath)
        except TypeError:
            if e == 'Not authorized':
                print('The account of this user is protected, we can not get its friends.')
            sys.exit(0)

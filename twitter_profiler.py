#!/usr/bin/env python
# -*- coding: utf-8 -*-
# encoding=utf8
# Copyright (c) 2018 Sebastian Garcia, eldracote
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
# This program started as a fork of the excelent program tweets_analyzer of @x0rz. Thanks to him and all contributors for making such a wondeful tool.
# Original code Copyright (c) 2017 @x0rz
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
# Install:
# pip install -r requirements.txt
# 
# Basic Usage:
# python twitter_profiler.py -n screen_name

from __future__ import unicode_literals
from ascii_graph import Pyasciigraph
from ascii_graph.colors import Gre, Yel, Red
from ascii_graph.colordata import hcolor
from collections import OrderedDict
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
from secrets import consumer_key, consumer_secret, access_token, access_token_secret, repustate_client
import pydot 
import pickle
import shutil
import json
from os import listdir
from os.path import isdir, join


__version__ = '0.5.3'
# The features dict is global because we dont want to store it in the user since all of its values are already there. Is only to put them together
features = {}

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
        #self.tweets = {}
        self.tweets = OrderedDict()
        self.tweets_detected_langs = collections.Counter()
        self.tweets_detected_sources = collections.Counter()
        self.tweets_detected_places = collections.Counter()
        self.geo_enabled_tweets = 0
        self.tweets_detected_hashtags = collections.Counter()
        self.tweets_detected_domains = collections.Counter()
        self.tweets_detected_timezones = collections.Counter()
        self.retweets = 0
        self.retweeted_users = collections.Counter()
        self.retweeted_users_names = {}
        self.tweets_mentioned_users = collections.Counter()
        self.id_screen_names = {}
        self.friends_timezone = collections.Counter()
        self.friends_lang = collections.Counter()
        self.friends_ids = {}
        self.friends = {}
        self.followers_ids = {}
        self.last_follower_retrieved_id = False
        self.followers = {}
        self.dirpath = ''
        self.last_friend_retrieved_id = False
        self.user_info = False
        # If the user is protected
        self.protected = False
        self.activity_hourly = { ("%2i:00" % i).replace(" ", "0"): 0 for i in range(24) }
        self.activity_weekly = { "%i" % i: 0 for i in range(7) }
        # Label of the user
        self.label = ""

    def analyze_features(self):
        """
        Computes the features for this profile
        """
        self.FFR = (float(self.user_info.followers_count) - self.user_info.friends_count) / (self.user_info.followers_count + self.user_info.friends_count)
        features['FFR'] = self.FFR
        features['retweets'] = self.retweets

    def analyze_sentiments(self):
        """
        For each twitt, analyze the sentiment
        """
        # 'add_filter', 'add_sentiment_rule', 'api_key', 'bulk_sentiment', 'categorize', 'chunk', 
        # 'clean_html', 'commit_sentiment_rules', 'delete_filter', 'delete_sentiment_rule', 
        # 'detect_language', 'entities', 'filter', 'function', 'host', 'list_filters', 
        # 'list_sentiment_rules', 'port', 'pos_tags', 'protocol', 'sentiment', 'topic_sentiment', 
        # 'url_template', 'usage', 'version']
        if args.color:
            def bold(text):
                return '\033[1m' + text + '\033[0m'
        else:
            def bold(text):
                return text
        print('[+] Sentiment Analysis of Tweets')
        counter = 50
        for twitt in self.tweets:
            if counter <= 0:
                break
            text = self.tweets[twitt].text.replace('\n',' ')
            try:
                language = repustate_client.detect_language(text.encode('utf-8'))['language']
                print('Sentiment: \033[1m{:16}\033[0m. Text: {}'.format(repustate_client.sentiment(text.encode('utf-8'), lang=language)['score'], text))
            except UnicodeEncodeError:
                print('\tEncode error with: {}'.format(text))
	    except Exception as inst:
		print 'Problem in analyze_sentiments () in class Processor'
		print type(inst)     # the exception instance
		print inst.args      # arguments stored in .args
		print inst           # __str__ allows args to printed directly
                print 'Text: {}'.format(text)
            counter -= 1

    def set_twitter_info(self, data):
        """ Sets the data of this user by hand.
        Useful if you first obtained the data from twitter before by other means and now you want to store it in its user object
        """
        self.user_info = data

    def get_twitter_info(self):
        """ Uses the twitter API to get info about the user. 
        Uses the name already stored in this object.
        This function is separated because the object can be used without asking Twitter.
        Since we store the complete Twitter object inside our object, we don't need to extract each value independently. We just use them.
        """
        try:
            self.user_info = twitter_api.get_user(self.screen_name)
            if args.debug > 2:
                print 'Twitter user aquired from API.'
            # If the user is protected, mark it now. We do this here so from now on the object can deal with this situation correctly
            self.protected = self.user_info.protected
            return True
        except tweepy.error.TweepError as e:
            if e[0][0]['code'] == 50: # 50 is user not found
                print('User not found!')
                shutil.rmtree(dirpath + name, ignore_errors=True)
                return False
            elif e[0][0]['code'] == 63: # your account is suspended
                print('User has been suspended')
                return False
            elif e[0][0]['code'] == 88: 
                #print('This user is protected and we can not get its data.')
                print('Rate Limit exceeded to query users. Wait some minutes and try again.')
                self.protected = True
                return False
            else:
                print e
                return False

    def get_tweets(self):
        """ Download Tweets from username account """
        tweets_still_to_retrieve = self.user_info.statuses_count - len(self.tweets)
        num_tweets = numpy.amin([args.maxtweets, tweets_still_to_retrieve])
        if args.offline or args.maxtweets <= 0:
            # Don't download, so we will use the tweets already in the cache
            return True
        else:
            # Download tweets
            try:
                if tweets_still_to_retrieve == 0:
                    # If the number of tweets to retrieve is zero, get out...
                    return True
                if len(self.tweets) < self.user_info.statuses_count:
                    print('[+] Tweets to Download. In cache: {}. Tweets in the account: {}. Downloading next {} tweets...'.format(len(self.tweets), self.user_info.statuses_count, num_tweets))
                    try:
                        # We do have a last tweet downloaded, continue from there...
                        last_tweet_obtained = self.tweets.keys()[-1]
                        if args.debug > 2:
                            print('The last downloaded twit was: {}'.format(last_tweet_obtained))
                        # This method can only return up to 3,200 of a user’s most recent Tweets
                        for status in tqdm(tweepy.Cursor(twitter_api.user_timeline, screen_name=self.screen_name, tweet_mode = 'extended').items(num_tweets), unit="tw", total=num_tweets):
                            # Create a new twitt
                            if not self.tweets.has_key(status.id):
                                #print 'NEW: {}'.format(status.id)
                                self.tweets[status.id] = status
                            else:
                                #print 'We had this tweet: {}'.format(status.id)
                                pass
                    except IndexError:
                        # No previous tweets downloaded, start fresh.
                        for status in tqdm(tweepy.Cursor(twitter_api.user_timeline, screen_name=self.screen_name).items(num_tweets), unit="tw", total=num_tweets):
                            # Create a new twit
                            self.tweets[status.id] = status
                    except:
                        print 'Unexpected error while retriving tweets in get_tweets()'
                else:
                    # The number of previous tweets and current tweets is the same, do not download them
                    if args.debug > 1:
                        print('The number of tweets stored in the cache is the same as the current number of tweets. Not downloading.')
                return True
            except KeyboardInterrupt:
                print('User suspended the download of tweets. Continuing with the analysis.')
                return True
            except tweepy.error.TweepError as e:
                try:
                    if e[0][0]['code'] == 63: # your account is suspended
                        print('User has been suspended')
                        return False
                    elif e[0][0]['code'] == 88: 
                        print('This user is protected and we can not get its data.')
                        self.protected = True
                        return False
                    elif e[0][0]['code'] == 401: 
                        print('Not authorized.')
                        return False
                except TypeError:
                    print e
                    if 'Twitter error response: status code = 401' in e:
                        print('Not Authorized for some reason')
                        return False

    def print_summary(self):
        """
        Print a summary of the account
        """
        # Print basic info
        self.print_basic_info()
        # Print info about the tweets
        self.print_tweets()
        # Print info about the friends
        self.print_friends_analysis()
        # Print info about the followers
        try:
            _temp = self.followers
        except AttributeError:
            self.followers = {}
            self.followers_ids = {}
            self.last_follower_retrieved_id = False
        self.print_followers_analysis()

    def add_label(self, label):
        """
        Assign a label to the user.
        For now, just one label
        """
        # Label format: float:str,str,str,str
        # Means: the float is the probability of being a human. This is the Label-What
        # The str are the categories for this account. This is the label-How
        # For example: 1:Troll,Social,Ads
        # For example: 0.5:Social,Ads,Authority
        try:
            label_what = float(label.split(':')[0])
            if label_what < 0 or label_what > 1:
                print('The label format is incorrect. The first part should be a float between 0 and 1')
                return False
        except:
            print('The label format is incorrect. The first part should be a float between 0 and 1')
            return False
        try:
            label_how = label.split(':')[1].split(',')
        except:
            return False
        if args.debug > 1:
            print 'Assigning the label: {}'.format(label)
        self.label = {'label_what':label_what, 'label_how':label_how}

    def export(self):
        """
        Export the data from this user to a file.
        The output is a json with this schema
        { 'User Twitter name':
                [ 
                'followers': [ <list of followers names> ], 
                'friends': [ <list of friends names> ],
                'label': ""
                ]
        }
        """
        if not self.label:
            print('The user can not be exported because it does not have a label yet.')
        else:
            # Store friends and followers on disk
            temp_dict = {}
            temp_dict[self.screen_name] = {}
            temp_dict[self.screen_name]['followers'] = []
            temp_dict[self.screen_name]['friends'] = []
            # Take this from the global featuers
            temp_dict[self.screen_name]['features'] = features
            try:
                temp_dict[self.screen_name]['followers'] = self.followers.keys()
                temp_dict[self.screen_name]['followers_ids'] = self.followers_ids
            except AttributeError:
                pass
            try:
                temp_dict[self.screen_name]['friends'] = self.friends.keys()
                temp_dict[self.screen_name]['friends_ids'] = self.friends_ids
            except AttributeError:
                pass
            temp_dict[self.screen_name]['label'] = self.label
            user_json = json.dumps(temp_dict)
            with open(dirpath + self.screen_name + '/' + self.screen_name + '-data.json', 'wb') as file:
                file.write(user_json)

    def print_tweets(self):
        """ Get the tweets and print them"""
        # Get the tweets first
        if self.tweets:
            # Analyze the tweets
            self.process_tweets()
            # Print them
            self.print_tweets_info()

    def process_tweets(self):
        """ Processing a single Tweet and updating our datasets """
        # text=u'Get th' # is_quote_status=False, # in_reply_to_status_id=None, # id=963923415663919104, # favorite_count=2, # '_json', # 'author', # 'contributors', # 'coordinates', # 'created_at', # 'destroy', # 'entities', # 'favorite', # 'favorite_count', # 'favorited', # 'geo', # 'id', # 'id_str', # 'in_reply_to_screen_name', # 'in_reply_to_status_id', # 'in_reply_to_status_id_str', # 'in_reply_to_user_id', # 'in_reply_to_user_id_str', # 'is_quote_status', # 'lang', # 'parse', # 'parse_list', # 'place', # 'possibly_sensitive', # 'retweet', # 'retweet_count', # 'retweeted', # 'retweets', # 'source', # 'source_url', # 'text', # 'truncated', # 'user' # source_url=u'http://twitter.com', 
        # Every time we process, we should reset the counters
        self.tweets_detected_langs = collections.Counter()
        self.tweets_detected_sources = collections.Counter()
        self.tweets_detected_places = collections.Counter()
        self.geo_enabled_tweets = 0
        self.tweets_detected_hashtags = collections.Counter()
        self.tweets_detected_domains = collections.Counter()
        self.tweets_detected_timezones = collections.Counter()
        self.tweets_mentioned_users = collections.Counter()
        self.retweeted_users = collections.Counter()
        self.retweets = 0
        self.activity_hourly = { ("%2i:00" % i).replace(" ", "0"): 0 for i in range(24) }
        self.activity_weekly = { "%i" % i: 0 for i in range(7) }
        for id in self.tweets:
            tweet = self.tweets[id]
            tw_date = tweet.created_at
            # Handling retweets
            # How many times the tweet was retweeted?
            # print(tweet.retweet_count)
            # How many times the tweet was favorited?
            # tweet.favorite_count
            # Was this tweet retweeted by others?
            # print(tweet.retweeted)
            # Do something with quoted tweets
            # print(tweet.is_quote_status)
            # Is this a reply tweet?
            # in_reply_to_status_id
            # Compute the amount of retweets of this user
            try:
                rtstatus = tweet.retweeted_status
                # Its a retweet
                self.retweets += 1
                rt_id_user = tweet.retweeted_status.user.id_str
                rt_name_user = tweet.retweeted_status.user.screen_name
                self.retweeted_users[rt_name_user] += 1
            except AttributeError:
                # Its a normal tweet
                pass
            # Adding timezone from profile offset to set to local hours
            if tweet.user.utc_offset:
                tw_date = (tweet.created_at + datetime.timedelta(seconds=tweet.user.utc_offset))
            if args.utc_offset:
                tw_date = (tweet.created_at + datetime.timedelta(seconds=args.utc_offset))
            # Updating our activity datasets (distribution maps)
            self.activity_hourly["{}:00".format(str(tw_date.hour).zfill(2))] += 1
            self.activity_weekly[str(tw_date.weekday())] += 1
            # Updating langs
            try:
                self.tweets_detected_langs[tweet.lang] += 1
            except KeyError:
                self.tweets_detected_langs[tweet.lang] = 1
            # Updating sources
            try:
                self.tweets_detected_sources[tweet.source] += 1
            except KeyError:
                self.tweets_detected_sources[tweet.source] = 1
            # Detecting geolocation
            if tweet.place:
                self.geo_enabled_tweets += 1
                try:
                    self.tweets_detected_places[tweet.place.name] += 1
                except KeyError:
                    self.tweets_detected_places[tweet.place.name] = 1
            # Updating hashtags list
            if tweet.entities['hashtags']:
                for ht in tweet.entities['hashtags']:
                    #ht['text'] = "#{}".format(ht['text'])
                    try:
                        self.tweets_detected_hashtags[ht['text']] += 1
                    except KeyError:
                        self.tweets_detected_hashtags[ht['text']] = 1
            # Updating domains list
            if tweet.entities['urls']:
                for url in tweet.entities['urls']:
                    domain = urlparse(url['expanded_url']).netloc
                    if domain != "twitter.com":  # removing twitter.com from domains (not very relevant)
                        try:
                            self.tweets_detected_domains[domain] += 1
                        except KeyError:
                            self.tweets_detected_domains[domain] = 1
            # Updating mentioned users list
            # The problem is that we should do this with IDs, not with screen names. But it was too dificult.
            if tweet.entities['user_mentions']:
                for ht in tweet.entities['user_mentions']:
                    try:
                        self.tweets_mentioned_users[ht['screen_name']] += 1
                    except KeyError:
                        self.tweets_mentioned_users[ht['screen_name']] = 1

    def print_tweets_info(self):
        """ Output the tweets"""
        self.print_stats(self.tweets_detected_langs, "[+] Top Languages from Tweets.")
        self.print_stats(self.tweets_detected_sources, "[+] Top Sources from Tweets.")
        if self.geo_enabled_tweets:
            print("[+] There are {} geo enabled tweet(s)".format(self.geo_enabled_tweets))
            print('')
        self.print_stats(self.tweets_detected_places, "[+] Top Places from Tweets.")
        self.print_stats(self.tweets_detected_hashtags, "[+] Top HashTags from Tweets.", top=10)
        self.print_stats(self.tweets_detected_domains, "[+] Top Domains from Tweets.")
        self.print_stats(self.tweets_detected_timezones, "[+] Top Timezones from Tweets.")
        self.print_stats(self.tweets_mentioned_users, "[+] Top Mentioned Users from Tweets.")
        self.print_stats(self.retweeted_users, "[+] Top Most retweeted users from Tweets.")
        self.print_charts(self.activity_hourly, "Daily activity distribution (per hour)")
        self.print_charts(self.activity_weekly, "Weekly activity distribution (per day)", weekday=True)

    def print_basic_info(self):
        """
        Print basic info about the user
        """
        if args.color:
            def bold(text):
                if type(text) == str:
                    return '\033[1m' + str(text.encode('utf-8')) + '\033[0m'
                elif type(text) == datetime.datetime or type(text) == int:
                    return '\033[1m' + str(text) + '\033[0m'
                else:
                    return '\033[1m' + text + '\033[0m'
        else:
            def bold(text):
                return text
        print('[+] User           : {}'.format(bold('@'+self.screen_name)))
        try:
            print('[+] What Label     : {}'.format(bold(str(self.label['label_what']))))
            print('[+] How Label      : {}'.format(self.label['label_how']))
        except AttributeError:
            print('[+] No Manual Label:')
        print('[+] Created on     : {}'.format(bold(self.user_info.created_at)))
        print('[+] Twitter ID     : {}'.format(bold(self.user_info.id)))
        print('[+] Current Date:  : {}'.format(bold(str(self.creation_time))))
        print('[+] lang           : {}'.format(bold(self.user_info.lang)))
        print('[+] geo_enabled    : {}'.format(bold(str(self.user_info.geo_enabled))))
        print('[+] time_zone      : {}'.format(bold(str(self.user_info.time_zone))))
        print('[+] utc_offset     : {}'.format(bold(str(self.user_info.utc_offset))))
        try:
            print('[+] FFR            : {} (Close to 1: Mostly Followed. Close to -1: Mostly follows.)'.format(bold(str(self.FFR))))
        except ZeroDivisionError:
            print('[+] FFR            : Und (Close to 1: Mostly Followed. Close to -1: Mostly follows.)')
        try:
            print('[+] Followers      : {}'.format(bold(str(self.user_info.followers_count))))
        except AttributeError:
            pass
        try:
            print('[+] Followers cache: {}'.format(bold(str(len(self.followers)))))
        except AttributeError:
            pass
        print('[+] Friends        : {}'.format(bold(str(self.user_info.friends_count))))
        print('[+] Friends cache  : {}'.format(bold(str(len(self.friends)))))
        print('[+] MemberPubLists : {}'.format(bold(str(self.user_info.listed_count))))
        print('[+] Location       : {}'.format(bold(self.user_info.location)))
        print('[+] Name           : {}'.format(bold(self.user_info.name)))
        print('[+] Protected      : {}'.format(bold(str(self.user_info.protected))))
        print('[+] Screen Name    : {}'.format(bold(self.screen_name)))
        print('[+] # Tweets       : {}'.format(bold(str(self.user_info.statuses_count))))
        print('[+] # Tweets cache : {}'.format(bold(str(len(self.tweets)))))
        print('[+] # ReTweets cache : {}'.format(bold(self.retweets)))
        print('[+] URL            : {}'.format(bold(str(self.user_info.url))))
        print('[+] Verified?      : {}'.format(bold(str(self.user_info.verified))))
        print('[+] Tweets liked   : {}'.format(bold(str(self.user_info.favourites_count))))
        print('[+] Default profile image: {}'.format(bold(str(self.user_info.default_profile_image))))
        try:
            censored = self.user_info.withheld_in_countries
        except Exception as e:
            censored = 'None'
        print('[+] Censored in countries : {}'.format(bold(censored)))
        print('')

    def print_followers(self):
        """ 
        Print only the info about followers
        """
        print('{},{},{}'.format(datetime.datetime.now(), self.screen_name, self.user_info.followers_count))

    def print_friends_analysis(self):
        """
        Analyze the friends of this user
        """
        # If the account is protected, we can not ask for its friends
        if not self.protected:
            print('[+] Analyzing {} friends.'.format(len(self.friends)))
            self.process_friends()
            self.print_stats(self.friends_lang, "[+] Top Friends languages.", top=10)
            self.print_stats(self.friends_timezone, "[+] Top Friends timezones.", top=10)

    def process_friends(self):
        """ Process all the friends """
        self.friends_timezone = collections.Counter()
        self.friends_lang = collections.Counter()
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

    def get_friends_twitter_api(self):
        """ use the api for getting friends """
        try:
            self.friends_ids = twitter_api.friends_ids(self.screen_name)
        except tweepy.error.TweepError as e:
            try:
                if e == 'Not authorized':
                    print('The account of this user is protected, we can not get its friends.')
                elif e[0][0]['code'] == 50: # 50 is user not found
                    return False
                elif e[0][0]['code'] == 63: # user suspended
                    return False
                elif e[0][0]['code'] == 88: # Rate limit
                    print("Rate limit exceeded to get friends data, we will sleep are retry in 15 minutes. The friends so far are stored.")
                    # Sleep
                    print('Waiting 5 minutes...')
                    time.sleep(300)
                    print('Resuming download...')
                    # Warning, this can loop
                    self.get_friends_twitter_api()
            except TypeError:
                print e

    def get_friends(self):
        """
        Get friends. Load friends from cache
        If offline, do not retrieve from twitter 
        If online and we have in the cache less than the limit, continue downloading from the last friend downloaded
        """
        # Are we offline? or we were asked to dowload 0 friends
        if args.offline or args.numfollowers <= 0:
            return True
        # If we are not offline and the user is not protected, try to get their friends
        elif not args.offline and not self.protected and len(self.friends) != self.user_info.friends_count:
            # Get the list of friends from twitter
            self.get_friends_twitter_api()
            if args.debug > 0:
                print('Total amount of friends this user follows: {}'.format(self.user_info.friends_count))
                print('Total amount of friends downloaded in cache: {}'.format(len(self.friends)))
            # If the limit requested is > than the amount we already have, continue downloading from where we left
            if self.last_friend_retrieved_id and self.last_friend_retrieved_id != self.friends_ids[-1]:
                if args.debug > 0:
                    print('We didn\'t finished downloading the list of friends. Continuing...')
                # We add one to download the list correctly
                try:
                    friends_to_continue_download = self.friends_ids[self.friends_ids.index(self.last_friend_retrieved_id) + 1:]
                except ValueError:
                    print 'We had an issue here. The last friend, saved to restored downloading, is not a friend anymore'
            else:
                friends_to_continue_download = self.friends_ids
            friends_to_download = friends_to_continue_download[:args.numfriends]
            print('Friends to download: Next {} (user has {} friends, {} in our cache)'.format(len(friends_to_download), self.user_info.friends_count, len(self.friends)))
            # We split the friends in groups in case we need to sleep because we are asking to much. Now not so used because we wait for the twitter exception
            amount_users = 0
            # This prints the bar
            with tqdm(total=len(friends_to_download), unit="user") as pbar:
                for friend_id in friends_to_download:
                        try:
                            pbar.update(1)
                            if args.debug > 1:
                                print('Downloading friend Nr {}: {}'.format(amount_users, friend_id))
                            try:
                                friend = twitter_api.get_user(friend_id)
                            except tweepy.error.TweepError as e:
                                try:
                                    if e == 'Not authorized':
                                        print('[+] The account of this user is protected, we can not get its friends.')
                                    elif e[0][0]['code'] == 88 or e[0][0]['code'] == 50:
                                        print("[+] Rate limit exceeded to get friends data, we will sleep are retry in 15 minutes. The friends so far are stored.")
                                    # Store this user so far
                                    pickle.dump(user, open( dirpath + name + '/' + name + '.data', "wb" ) )
                                    # Sleep
                                    print('Waiting 15 minutes...')
                                    time.sleep(900)
                                    print('Resuming download...')
                                    # Retrieve the same last user that we couldn't before
                                    friend = twitter_api.get_user(friend_id)
                                    continue
                                except TypeError:
                                    # For some reason the error from twitter not always can be indexed...
                                    print e
                                    # catch all? What are we doing here?
                                    print('Weird error {}'.format(e))
                                    print('Save user just in case.')
                                    pickle.dump(user, open( dirpath + name + '/' + name + '.data', "wb" ) )
                            except Exception as e:
                                # catch all? What are we doing here?
                                print('Weird error {}'.format(e))
                                print('Save user just in case.')
                                pickle.dump(user, open( dirpath + name + '/' + name + '.data', "wb" ) )
                            UserFriend = User(friend.screen_name)
                            UserFriend.set_twitter_info(friend)
                            self.friends[friend.screen_name] = UserFriend
                            self.last_friend_retrieved_id = UserFriend.user_info.id
                            amount_users += 1
                        except KeyboardInterrupt:
                            # Print Summary of detections in the last Time Window
                            print('Keyboard Interrupt. Storing the user so far.')
                            pickle.dump(user, open( dirpath + name + '/' + name + '.data', "wb" ) )
                            return True
            # Store the friends at the end
            pickle.dump(user, open( dirpath + name + '/' + name + '.data', "wb" ) )
        # Finally continue processing the friends

    def print_followers_analysis(self):
        """
        Analyze the followers of this user
        """
        # If the account is protected, we can not ask for its followers
        if not self.protected:
            try:
                print('[+] Analyzing {} followers.'.format(len(self.followers)))
                self.process_followers()
                self.print_stats(self.followers_lang, "[+] Top Followers languages.", top=10)
                self.print_stats(self.followers_timezone, "[+] Top Followers timezones.", top=10)
            except AttributeError:
                pass

    def process_followers(self):
        """ Process all the followers """
        self.followers_timezone = collections.Counter()
        self.followers_lang = collections.Counter()
        for follower in self.followers:
            try:
                if self.followers[follower].user_info.lang:
                    self.followers_lang[self.followers[follower].user_info.lang] += 1
                if self.followers[follower].user_info.time_zone:
                    self.followers_timezone[self.followers[follower].user_info.time_zone] += 1
            except AttributeError:
                if args.debug > 2:
                    print('Processing Friend {}'.format(follower))
                    print 'The follower does not have data!'

    def get_followers_twitter_api(self):
        """ use the api for getting followers """
        try:
            self.followers_ids = twitter_api.followers_ids(self.screen_name)
        except tweepy.error.TweepError as e:
            try:
                if e == 'Not authorized':
                    print('The account of this user is protected, we can not get its followers.')
                elif e[0][0]['code'] == 50: # 50 is user not found
                    return False
                elif e[0][0]['code'] == 63: # user suspended
                    return False
                elif e[0][0]['code'] == 88: # Rate limit
                    print("Rate limit exceeded to get followers data, we will sleep are retry in 15 minutes. The followers so far are stored.")
                    # Sleep
                    print('Waiting 5 minutes...')
                    time.sleep(300)
                    print('Resuming download...')
                    # Warning, this can loop
                    self.get_followers_twitter_api()
            except TypeError:
                print e

    def get_followers(self):
        """
        Get followers. Load followers from cache
        If offline, do not retrieve from twitter 
        If online and we have in the cache less than the limit, continue downloading from the last followers downloaded
        """
        # Try to cache some old users where we don't have the followers yet
        try: 
            temp = self.followers
        except AttributeError:
            self.followers = []
        try: 
            temp = self.last_follower_retrieved_id
        except AttributeError:
            self.last_follower_retrieved_id = False
        # Are we offline? or we were asked to dowload 0 followers
        if args.offline or args.numfollowers <= 0:
            return True
        # If we are not offline and the user is not protected, try to get their followers
        elif not args.offline and not self.protected and len(self.followers) != self.user_info.followers_count:
            # Get the list of followers from twitter
            self.get_followers_twitter_api()
            if args.debug > 0:
                print('Total amount of followers that follow this user: {}'.format(self.user_info.followers_count))
                print('Total amount of followers downloaded in cache: {}'.format(len(self.followers)))
            # If the limit requested is > than the amount we already have, continue downloading from where we left
            if self.last_follower_retrieved_id and self.last_follower_retrieved_id != self.followers_ids[-1]:
                if args.debug > 0:
                    print('We didn\'t finished downloading the list of followers. Continuing...')
                followers_to_continue_download = self.followers_ids[self.followers_ids.index(self.last_follower_retrieved_id) + 1:]
            else:
                followers_to_continue_download = self.followers_ids
            followers_to_download = followers_to_continue_download[:args.numfollowers]
            print('Followers to download: Next {} (user has {} followers, {} in our cache)'.format(len(followers_to_download), self.user_info.followers_count, len(self.followers)))
            # We split the followers in groups in case we need to sleep because we are asking to much. Now not so used because we wait for the twitter exception
            amount_users = 0
            # This prints the bar
            with tqdm(total=len(followers_to_download), unit="user") as pbar:
                for follower_id in followers_to_download:
                        try:
                            pbar.update(1)
                            if args.debug > 1:
                                print('Downloading follower Nr {}: {}'.format(amount_users, follower_id))
                            try:
                                follower = twitter_api.get_user(follower_id)
                            except tweepy.error.TweepError as e:
                                try:
                                    if e == 'Not authorized':
                                        print('[+] The account of this user is protected, we can not get its followers.')
                                    elif e[0][0]['code'] == 88 or e[0][0]['code'] == 50:
                                        print("[+] Rate limit exceeded to get followers data, we will sleep are retry in 15 minutes. The followers so far are stored.")
                                    # Store this user so far
                                    pickle.dump(user, open( dirpath + name + '/' + name + '.data', "wb" ) )
                                    # Sleep
                                    print('Waiting 15 minutes...')
                                    time.sleep(900)
                                    print('Resuming download...')
                                    # Retrieve the same last user that we couldn't before
                                    follower = twitter_api.get_user(follower_id)
                                    continue
                                except TypeError:
                                    # For some reason the error from twitter not always can be indexed...
                                    print e
                                    # catch all? What are we doing here?
                                    print('Weird error {}'.format(e))
                                    print('Save user just in case.')
                                    pickle.dump(user, open( dirpath + name + '/' + name + '.data', "wb" ) )
                            except Exception as e:
                                # catch all? What are we doing here?
                                print('Weird error {}'.format(e))
                                print('Save user just in case.')
                                pickle.dump(user, open( dirpath + name + '/' + name + '.data', "wb" ) )
                            UserFriend = User(follower.screen_name)
                            UserFriend.set_twitter_info(follower)
                            self.followers[follower.screen_name] = UserFriend
                            self.last_follower_retrieved_id = UserFriend.user_info.id
                            amount_users += 1
                        except KeyboardInterrupt:
                            # Print Summary of detections in the last Time Window
                            print('Keyboard Interrupt. Storing the user so far.')
                            pickle.dump(user, open( dirpath + name + '/' + name + '.data', "wb" ) )
                            return True
            # Store the followers at the end
            pickle.dump(user, open( dirpath + name + '/' + name + '.data', "wb" ) )
        # Finally continue processing the followers

    def print_stats(self, dataset, text, top=5):
        """ Displays top values of something by order """
        sum = numpy.sum(list(dataset.values()))
        i = 0
        if sum:
            print(text + ' (Total {} objects in this category).'.format(len(list(dataset.values()))))
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
            print("")

    def print_charts(self, dataset, title, weekday=False):
        """ Prints nice charts based on a dict {(key, value), ...} """
        if dataset.values().count(0) != len(dataset.values()):
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
            for line in graph.graph(title + ' ({} tweets)'.format(len(self.tweets)), data):
                print('{}'.format(line))
            print("")

def plot_users(users, dirpath):
    """ Read the friends of these users from a file and plot a graph"""
    print('Plotting a unique graph for all users')
    #pygraph = pydot.Dot(graph_type='graph', resolution='1400000')
    #pygraph = pydot.Dot(graph_type='graph', resolution='32000')
    pygraph = pydot.Dot(graph_type='graph', resolution='300')
    #pygraph.set('center', '1')
    #pygraph.set('ratio', 'auto')
    pygraph.set_fontsize('21')
    #pygraph.set_ranksep('4 equally')
    #pygraph.set_rankdir('LR')
    counter_papa = {}
    color_node = {}
    counter_for_user = 0
    # First count how many times each node is referenced
    for user in users.split(','):
        # read their friends
        try:
            datapath = os.path.expanduser(dirpath + user + '/' + user + '.data')
            user_object = pickle.load(open(datapath, 'rb'))
            friends = user_object.friends.keys()
        except IOError:
            # This user is not in the cache
            continue
        for friend in list(set(friends)):
            try:
                counter_papa[friend] += 1
            except KeyError:
                counter_papa[friend] = 1
            counter_for_user += 1
        print('User {} had {} nodes.'.format(user, counter_for_user))
        counter_for_user = 0
    # Adding colors
    if args.debug > 0:
        print('Putting the color in the nodes.')
    for node in counter_papa:
        if counter_papa[node] == 1:
            color_node[node] = 'LightBlue'
        elif counter_papa[node] == 2:
            color_node[node] = 'Red'
        elif counter_papa[node] == 3:
            color_node[node] = 'Yellow'
        elif counter_papa[node] == 4:
            color_node[node] = 'Blue'
        elif counter_papa[node] == 5:
            color_node[node] = 'Orange'
        elif counter_papa[node] == 6:
            color_node[node] = 'crimson'
        elif counter_papa[node] == 7:
            color_node[node] = 'forestgreen'
        elif counter_papa[node] == 8:
            color_node[node] = 'deeppink'
        elif counter_papa[node] == 9:
            color_node[node] = 'cadetblue'
        elif counter_papa[node] == 10:
            color_node[node] = 'aquamarine'
        else:
            color_node[node] = 'white'
    # Delete the secondary nodes that had less than certain amount of edges to them
    try:
        minnodes = args.minnumnsharednodes
    except AttributeError:
        minnodes = 0
    count_reviewed = 0
    for user in users.split(','):
        if args.debug > 1:
            print('User: {}'.format(user))
        # read their friends
        try:
            datapath = os.path.expanduser(dirpath + user + '/' + user + '.data')
            user_object = pickle.load(open(datapath, 'rb'))
            friends = user_object.friends.keys()
        except IOError:
            # This user is not in the cache
            continue
        # Add the main nodes
        if pygraph.get_node(user) == []:
            node = pydot.Node(user,fontcolor='black',shape='rectangle')
            node.set_group('First')
            node.set_style('filled')
            node.set_fontsize('36')
            node.set_color('red')
            node.set_fontname('Times-Bold')
            node.set_fontcolor('yellow')
            node.set_fillcolor('black')
            pygraph.add_node(node)
            count_reviewed += 1
            if args.debug > 1:
                print('Add node: {} is {}'.format(node.get_name(), count_reviewed))
        for friend in list(set(friends)):
            if args.debug > 1:
                print('\tEvaluating Friend: {}, has {} links'.format(friend, counter_papa[friend]))
            if counter_papa[friend] > minnodes:
                # Add the secondary nodes
                if pygraph.get_node(friend) == []:
                    node = pydot.Node(friend,fontcolor='black')
                    node.set_group('Second')
                    node.set_style('filled')
                    node.set_fillcolor(color_node[node.get_name().replace('"','')])
                    pygraph.add_node(node)
                    count_reviewed += 1
                    if args.debug > 1:
                        print('\t\tAdd node: {} is {}'.format(node.get_name(), count_reviewed))
                # Make the edge
                edge = pydot.Edge(user, friend)
                pygraph.add_edge(edge)
    print('Total nodes processed: {}'.format(count_reviewed))
    nodes = pygraph.get_node_list()
    print('Amount of nodes in the graph: {}'.format(len(nodes)))
    if args.debug > 0:
        print ('Colors in the graph:')
        print ('Share 1 follower: LightBlue')
        print ('Share 2 followers: Red')
        print ('Share 3 followers: Yellow')
        print ('Share 4 followers: Blue')
        print ('Share 5 followers: Orange')
        print ('Share 6 followers: Crimson')
        print ('Share 7 followers: Forest Green')
        print ('Share 8 followers: Deep Pink')
        print ('Share 9 followers: Cadet Blue')
        print ('Share 10 followers: Aquamarine')
        print ('Share >10 followers: White')
    pygraph.write_png('graph.png')
    pygraph.write_dot('graph.dot')


def list_users_in_db():
    # List the cache
    list_of_users = os.listdir(dirpath)
    composite_list = [list_of_users[x:x+10] for x in range(0, len(list_of_users),10)]
    for list in composite_list:
        for user in list:
            print('+ {:17}'.format(user)),
        print('')


if __name__ == '__main__':
    try:
	set_output_encoding()
        # Process Parameters
        parser = argparse.ArgumentParser(description="Twitter Profiler version %s. Author: Sebastian Garcia (eldraco@gmail.com, @eldracote). Based on original code of @x0rz." % __version__, usage='%(prog)s -n <screen_name> [options]')
        parser.add_argument('-n', '--names', required=False, metavar="screen_names", help='Target screen_names. Can be a comma separated list of names for multiple comparisons and multiple download of data.')
        parser.add_argument('-l', '--limit', type=int, default=1000, help='Limit the number of tweets to retreive (default=1000)')
        parser.add_argument('--no-timezone', action='store_true', help='Removes the timezone auto-adjustment (default is UTC)')
        parser.add_argument('--utc-offset', type=int, help='Manually apply a timezone offset (in seconds)')
        parser.add_argument('-s', '--nosummary', action='store_true', default=False, help='Do not show the summary of the user.')
        parser.add_argument('-F', '--quickfollowers', action='store_true', help='Print only a very short summary about the number of followers for the users. Useful to run with cron and store the results.')
        parser.add_argument('-c', '--color', action='store_true', help='Do not  Use colors when printing', default=True)
        parser.add_argument('-N', '--numfriends', action='store', help='Max amount of friends to retrieve. Defaults to 200. Use -1 to retrieve all of them. Warning! this can take long, since twitter limits 700 friends requests every 15mins approx.', default=200, type=int)
        parser.add_argument('-O', '--numfollowers', action='store', help='Max amount of followers to retrieve. Defaults to 200. Use -1 to retrieve all of them. Warning! this can take long, since twitter limits 700 followers requests every 15mins approx.', default=200, type=int)
        parser.add_argument('-o', '--offline', action='store_true', default=False, help='Use the offline data stored in cache for all the actions. Do not retrieve them from Twitter (use after you retrieved it at least once).')
        parser.add_argument('-d', '--debug', action='store', type=int, default=0, help='Debug level.')
        parser.add_argument('-t', '--maxtweets', action='store', type=int, default=1000, help='Maximum amount of tweets to download for analysis per user.')
        parser.add_argument('-x', '--redocache', action='store_true', help='Delete all the cache data for this user and download again. Useful if the cache becomes corrupted.')
        parser.add_argument('-i', '--listcacheusers', action='store_true', help='List the users in the cache.')
        parser.add_argument('-g', '--graphusers', action='store_true', help='Get the list of users specified with -n, read their _offline_ data, and create a unique graph for all their shared friends. Two files are generated: graph.png and graph.dot. The PNG is an image with basic properties. The dot file is for you to play and improve the graph (e.g. cat graph.dot |sfdp -Tpng -o graph2.png). Use -m to limit the minimum amount of shared connections you want in the graph.')
        parser.add_argument('-m', '--minnumnsharednodes', action='store', help='Together with -g for making a graph, this options selects the minimum amount of shared friends to put in the graph as nodes. Defaults to 2', default=2, type=int)
        parser.add_argument('-S', '--sentiment', action='store_true', help='Analyze the sentiment of each twitt', default=False)
        parser.add_argument('-L', '--label', action='store', required=False, type=str, help='Label to assign to this Twitter user. For humans use human, for bots use bot, for trolls use troll. ', default=False)
        parser.add_argument('-e', '--export', action='store_true', help='Export the data of this user in his folder called <username>-data.json', default=False)
        parser.add_argument('-a', '--all', action='store_true', help='Apply the selected actions to all the users in the database.', default=False)
        args = parser.parse_args()

        # The path everyone uses to access the cache
        dirpath = os.path.expanduser('~/.twitter_analyzer_users/')

        # If we want to plot users offline, we don't need even to connect to twitter. Do it and exit
        if args.graphusers:
            plot_users(args.names, dirpath)
            sys.exit(0)

        # If we have to list, just list
        if args.listcacheusers:
            list_users_in_db()
            sys.exit(0)

        # Connect to Twitter from now on
        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(access_token, access_token_secret)
        twitter_api = tweepy.API(auth)

        # Do we have names to process, or all the database?
        if args.all:
            names = [f for f in listdir(dirpath) if isdir(join(dirpath, f))]
        elif not args.all:
            names = args.names.split(',')

        # Go user by user given
        if names:
            for name in names:
                print('\nProcessing the name {}.'.format(name))
                try:

                    # Should we delete the cache for this user?
                    if args.redocache:
                        print 'Deleteing all the cache from this user and starting again.'
                        shutil.rmtree(dirpath + name, ignore_errors=True)

                    # Create our folder if we need it, and the user object
                    try:
                        os.makedirs(dirpath + name)
                        # It does not exist yet
                        if args.debug > 1:
                            print('Folders created in {}'.format(dirpath + name))
                        user = User(name)
                    except OSError:
                        # Already exists
                        exists = True
                        if args.debug > 1:
                            print('The user {} exists, loading its data.'.format(name))
                        # Load what we know from this user
                        # We always load the cache, if we are offline or not.
                        try:
                            datapath = os.path.expanduser(dirpath + name + '/' + name + '.data')
                            # This takes time
                            user = pickle.load(open(datapath, 'rb'))
                        except IOError:
                            user = User(name)
                    user.dirpath = dirpath


                    # If offline, load the file only, if online, get more data
                    # Get basic info from twitter if we are not offline. If offline, get the cache
                    if not args.offline:
                        if args.debug > 1:
                            print('Getting basic twitter info.')
                        #
                        # Here is where most of the stuff happens, donwloading data from twitter api
                        # Get basic info
                        exists = user.get_twitter_info()
                        if exists and not user.protected:
                            # Get friends
                            user.get_friends()
                            # Get followers
                            user.get_followers()
                            # Get twitts
                            user.get_tweets()

                    ############################
                    # After downloading the data (or not if offline) do things with it
                    if exists:
                        # Add the label
                        if args.label:
                            # Adding the label can fail because of the format
                            if user.add_label(args.label) == False:
                                sys.exit(-1)
                        # Only show the amount of friends
                        if args.quickfollowers:
                            user.print_followers()
                        if args.sentiment:
                            user.analyze_sentiments()
                        # Analyze features of the profile
                        user.analyze_features()
                        # Option by default, print a Summary of the account, including the friends
                        if not args.nosummary:
                            # To protect from offline asking of unknown users
                            if args.offline and not user.user_info:
                                print('The user {} is not in our cache database.'.format(user.screen_name))
                                sys.exit(0)
                            user.print_summary()
                        # Export the data to disk
                        if args.export:
                            user.export()
                        # Always Store this user in our disk cache
                        pickle.dump(user, open( dirpath + name + '/' + name + '.data', "wb" ) )
                except KeyboardInterrupt:
                    # Print Summary of detections in the last Time Window
                    print('Keyboard Interrupt. Storing the user')
                    pickle.dump(user, open( dirpath + name + '/' + name + '.data', "wb" ) )

    except tweepy.error.TweepError as e:
        print("[\033[91m!\033[0m] Twitter error: {}".format(e))
        try:
            if e[0][0]['code'] == 50:
                # user not found
                shutil.rmtree(dirpath + name, ignore_errors=True)
        except TypeError:
            if e == 'Not authorized':
                print('The account of this user is protected, we can not get its friends.')
            sys.exit(0)

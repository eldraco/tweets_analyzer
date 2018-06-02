# Twitter Profiler 

Twitter Profiler is a tool to download data about users in Twitter and analyze it in a simple manner. The tool implements some basic statistics about the usage patterns of the user and attempts to profile the user. The goal of the tool is to analyze the features and properties of users in Twitter and help identify different types of users. Twitter Profiler implements a comparison of users by plotting the shared friends of multiple users. It can take a large amount of users, analyze who they follow (friends) and graph only those friends that are followed by a defined amount of users. 

It answers the question: Which users are followed simultaneously by the accounts xx,yy,zz,aa,bb? 

## Features

- You can ask for one user or multiple users simultaneously. The program will handle the API and timings in order to download everything.
- Average tweet activity, by hour and by day of the week
- Timezone and language set for the Twitter interface
- Sources used (mobile application, web browser, ...)
- Geolocations
- Most used hashtags, most retweeted users and most mentioned users
- Friends analysis based on most frequent timezones/languages


### Installation

⚠ First, update your API keys in the *secrets.py* file. To get API keys go to https://apps.twitter.com/

Python v2.7 or newer is required

You will need the following python packages installed: tweepy, ascii_graph, tqdm, numpy

```sh
pip install -r requirements.txt
```


### Usage

```
usage: twitter_profiler.py -n <screen_name> [options]

Twitter Profiler version 0.4. Author: Sebastian Garcia (eldraco@gmail.com,
@eldracote). Based on original code of @x0rz.

optional arguments:
  -h, --help            show this help message and exit
  -n screen_names, --names screen_names
                        Target screen_names. Can be a comma separated list of
                        names for multiple comparisons and multiple download
                        of data.
  -l LIMIT, --limit LIMIT
                        Limit the number of tweets to retreive (default=1000)
  --no-timezone         Removes the timezone auto-adjustment (default is UTC)
  --utc-offset UTC_OFFSET
                        Manually apply a timezone offset (in seconds)
  -s, --nosummary       Do not show the summary of the user.
  -F, --quickfollowers  Print only a very short summary about the number of
                        followers for the users. Useful to run with cron and
                        store the results.
  -c, --color           Use colors when printing
  -N NUMFRIENDS, --numfriends NUMFRIENDS
                        Max amount of friends to retrieve. Defaults to 200.
                        Use -1 to retrieve all of them. Warning! this can take
                        long, since twitter limits 700 friends requests every
                        15mins approx.
  -o, --offline         Use the offline data stored in cache for all the
                        actions. Do not retrieve them from Twitter (use after
                        you retrieved it at least once).
  -d DEBUG, --debug DEBUG
                        Debug level.
  -t MAXTWEETS, --maxtweets MAXTWEETS
                        Maximum amount of tweets to download for analysis per
                        user.
  -x, --redocache       Delete all the cache data for this user and download
                        again. Useful if the cache becomes corrupted.
  -i, --listcacheusers  List the users in the cache.
  -g, --graphusers      Get the list of users specified with -n, read their
                        _offline_ data, and create a unique graph for all
                        their shared friends. Two files are generated:
                        graph.png and graph.dot. The PNG is an image with
                        basic properties. The dot file is for you to play and
                        improve the graph (e.g. cat graph.dot |sfdp -Tpng -o
                        graph2.png). Use -m to limit the minimum amount of
                        shared connections you want in the graph.
  -m MINNUMNSHAREDNODES, --minnumnsharednodes MINNUMNSHAREDNODES
                        Together with -g for making a graph, this options
                        selects the minimum amount of shared friends to put in
                        the graph as nodes. Defaults to 2
```

# TODO
- Download the id of followers and friends instead of the complete objects
- Store the data in a neo4j
- Compute new features
- The language of tweets make it only for not retweeted tweets
- For computing user mentions, use ids and not screen names
- compare two users
- Give me one user and monitor it in real time continually. Store new and old followers, etc.

### Example output

![Twitter account activity]()

License
----
GNU GPLv3

# -*- coding: utf-8 -*-
import argparse
import collections
import copy
import datetime
import dateutil.parser
import json
import urllib
import urllib2


GET, POST = range(2)

hostname = None
port = None


"""
This script uses a toy example with three songs being played on two
channels. It first posts the data on the server, then makes a few calls and
checks that the data returned by the server is equal to what is expected.
"""


def decode_date(d):
    """
    The server sent us a date in the ISO format. Convert it to a datetime
    python object.
    """
    return dateutil.parser.parse(d)


def get_response(fct, data, method=GET):
    """
    Performs the query to the server and returns a string containing the
    response.
    """
    assert(method in (GET, POST))
    url = 'http://%s:%s/%s' % (hostname, port, fct)
    if method == GET:
        req = urllib2.Request('%s?%s' % (url, urllib.urlencode(data)))
    elif method == POST:
        # XXX: Pass data as a JSON body to match the API specification
        # req = urllib2.Request(url, urllib.urlencode(data))
        req = urllib2.Request(url, json.dumps(data), {'Content-Type': 'application/json'})
    response = urllib2.urlopen(req)
    return response.read()


# performer, title, length (in seconds)
song1 = (u"Performer1", u"Song1", 600)
song2 = (u"Performer2", u"Song2", 180)
song3 = (u"Pêrformer3", u"Söng3", 180)

# channel -> plays
plays = {
    'Channel1': {
        # year, month, day, hour, minute, second
        (2014, 1, 1, 1, 0, 0): song1,
        (2014, 1, 1, 2, 0, 0): song2,
        (2014, 1, 1, 3, 0, 0): song3,
        (2014, 1, 1, 4, 0, 0): song1,
        (2014, 1, 8, 1, 0, 0): song3,
        (2014, 1, 9, 1, 0, 0): song3,
        (2014, 1, 10, 1, 0, 0): song3,
        (2014, 1, 11, 1, 0, 0): song2},
    'Channel2': {
        (2014, 1, 1, 1, 0, 0): song2,
        (2014, 1, 1, 2, 0, 0): song2,
        (2014, 1, 1, 3, 0, 0): song2,
        (2014, 1, 1, 4, 0, 0): song2,
        (2014, 1, 8, 1, 0, 0): song1,
        (2014, 1, 9, 1, 0, 0): song1}
}


def add_plays():
    """
    For each play listed above, first add the necessary metadata: channels,
    performers, songs, then the actual plays. Note that the metadata is posted
    more than once: if the data already exists on the server, it shouldn't be
    added again.
    """
    for channel in plays.keys():
        get_response("add_channel", {"name": channel}, method=POST)
        for start, (performer, title, length) in plays[channel].iteritems():
            get_response("add_performer", {"name": performer.encode('utf8')},
                         method=POST)
            get_response("add_song", {"performer": performer.encode('utf8'),
                                      "title": title.encode('utf8')},
                         method=POST)
            start = datetime.datetime(*start)
            end = start + datetime.timedelta(seconds=length)
            get_response("add_play",
                         {"performer": performer.encode('utf8'),
                          "title": title.encode('utf8'),
                          "channel": channel.encode('utf8'),
                          "start": start.isoformat(), "end": end.isoformat()},
                         method=POST)


def check_channel_plays():
    """
    Get the plays for the two channels separately.

    The server should return something like this:

    {result: [
     {'performer': 'Performer1', 'title': 'Song1',
      'start': '2014-01-10T01:00:00',
      'end': '2014-01-10T01:03:00'],
     {'performer': 'Performer2', 'title': 'Song2',
      'start': '2014-01-01T03:00:00',
       'end': '2014-01-01T03:03:00'},...], code: 0}
    """
    for channel in plays.keys():
        chan_plays = {}
        res = json.loads(get_response('get_channel_plays', {
            "channel": channel,
            "start": datetime.datetime(2013, 1, 1).isoformat(),
            "end": datetime.datetime(2015, 1, 1).isoformat()
        }))
        assert(res['code'] == 0)
        channel_plays = res['result']
        for data in channel_plays:
            performer = unicode(data['performer'])
            title = unicode(data['title'])
            start = decode_date(data['start'])
            end = decode_date(data['end'])
            chan_plays[
                (start.year, start.month, start.day,
                 start.hour, start.minute, start.second)] = (
                     performer, title, (end - start).total_seconds())
        assert(chan_plays == plays[channel])


def get_song_plays(song):
    """
    Filter the play dictionary for this particular song.
    """
    song_plays = copy.deepcopy(plays)
    for channel in song_plays.keys():
        banned = [date for date in song_plays[channel].keys() if
                  song_plays[channel][date] != song]
        for b in banned:
            del song_plays[channel][b]
        if not song_plays[channel]:
            del song_plays[channel]
    return song_plays


def check_song_plays():
    """
    Check the plays for one particular song. Here the results should look like
    this:

    {result: [
     {'channel': 'channel1', 'start': '2014-01-10T01:00:00',
      'end': '2014-01-10T01:03:00'},
     {'channel': 'channel2', 'start': '2014-01-01T02:00:00',
      'end': '2014-01-01T02:03:00'}, ...], code: 0}
    """
    song3_res = json.loads(get_response('get_song_plays', {
        "performer": song3[0].encode('utf8'),
        "title": song3[1].encode('utf8'),
        "start": datetime.datetime(2013, 1, 1).isoformat(),
        "end": datetime.datetime(2015, 1, 1).isoformat()
    }))
    assert(song3_res['code'] == 0)
    song3_plays = song3_res['result']
    # adapt what we got from the server to compare it to the dictionary of
    # plays defined above. We want:
    # {channel: {date: song}}
    test_plays = {}
    for data in song3_plays:
        channel = data['channel']
        start = decode_date(data['start'])
        end = decode_date(data['end'])
        if channel not in test_plays:
            test_plays[channel] = {}
        test_plays[channel][
            (start.year, start.month, start.day, start.hour,
             start.minute, start.second)] = (song3[0],
                                             song3[1],
                                             (end - start).seconds)
    assert(test_plays == get_song_plays(song3))


def get_top(start, channels):
    """
    Convert the play dict into a list comparable to what the server returns
    (see check_top).
    """
    pc = collections.defaultdict(int)
    previous_pc = collections.defaultdict(int)
    end = start + datetime.timedelta(days=7)
    previous_start = start - datetime.timedelta(days=7)
    for channel in plays.keys():
        if channel not in channels:
            continue
        for date, (performer, title, length) in plays[channel].iteritems():
            date = datetime.datetime(*date)
            if start <= date < end:
                pc[(performer, title)] += 1
            elif previous_start <= date < start:
                previous_pc[(performer, title)] += 1
    res = []
    previous_pos = sorted(previous_pc.keys(), key=lambda s: -previous_pc[s])
    for song in pc.keys():
        try:
            prev = previous_pos.index(song)
        except ValueError:
            prev = None
        res.append(
            {'performer': song[0], 'title': song[1],
             'plays': pc[song], 'previous_plays': previous_pc[song],
             'previous_rank': prev})
    res = sorted(res, key=lambda x: -x['plays'])
    for i, r in enumerate(res):
        res[i]['rank'] = i
    return res


def check_top():
    """
    Here we expect a list of [performer, song, plays, previous plays, previous
    rank]. Previous ranks starts at 0. If the song was not in the list for the
    past, the previous rank should be null.

    {result: [
     {'performer': 'Performer1', 'title': 'Song1', 'rank': 0,
      'previous_rank': 2, 'plays': 1, 'previous_plays': 2},...],
     'code': 0}
    """
    res = json.loads(get_response('get_top', {
        "channels": json.dumps(plays.keys()),
        "start": datetime.datetime(2014, 1, 8).isoformat(),
        "limit": 10
    }))
    assert(res['code'] == 0)
    top = res['result']
    assert(top == get_top(datetime.datetime(2014, 1, 8), plays.keys()))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Web Crawler')
    parser.add_argument('-H', action="store", dest="hostname",
                        default="localhost", type=str)
    parser.add_argument('-P', action="store", dest="port",
                        default=5000, type=int)
    parser.add_argument('--add-data', action="store_true", dest="add_data",
                        help=("Insert test data (only use the first time you "
                              "run the script"), default=False)

    args = parser.parse_args()
    hostname = args.hostname
    port = args.port
    if args.add_data:
        add_plays()
    check_channel_plays()
    check_song_plays()
    check_top()
    print "Success!"

# -*- coding: utf-8 -*-
import json
import logging
from datetime import timedelta

from flask import Blueprint, jsonify, request

from .models import Song, Performer, Channel, PlayByChannel, PlayBySong, _recreate_keyspace
from .schemas import channel_schema, performer_schema, song_schema, play_by_channel_schema, play_by_song_schema, request_schema, channels_param_schema
from .exceptions import PlaysException
import topk

logger = logging.getLogger()

api = Blueprint('api', __name__)


def _get_request_parameters(required=None):    
    params = {
        item[0]: item[1]
        for item in request.args.items()
    }

    d = request_schema.load(
        params, 
        required=required
    )
    _format_errors(d.errors)


        
    return d.data

    
def _format_errors(errors):
    """Convert Marshmallow's error dictionary to a list of strings"""
    errors = [v for v in errors.values()]
    if errors:
        raise PlaysException(code=400, errors=errors)


def _get_object(schema):
    """
    Retrieve the request body, validate and deserialize it into a model object.
    """
    j = request.get_json(force=True)

    obj = schema.load(j)
    _format_errors(obj.errors)

    return obj.data


def _get_representation(obj, schema):
    """Takes a model and transforms into serializable object"""
    rep = schema.dump(obj)
    _format_errors(rep.errors)
    return rep.data


@api.route('/add_channel', methods=['POST'])
def add_channel():
    obj = _get_object(channel_schema)
    obj.save()
    rep = _get_representation(obj, channel_schema)
    return jsonify(code=0, result=rep)


@api.route('/add_performer', methods=['POST'])
def add_performer():
    obj = _get_object(performer_schema)
    obj.save()
    rep = _get_representation(obj, performer_schema)
    return jsonify(code=0, result=rep)


@api.route('/add_song', methods=['POST'])
def add_song():
    obj = _get_object(song_schema)
    obj.save()
    
    # Make sure that the performer is inserted in the database
    performer = Performer(name=obj.performer)
    performer.save()
    
    rep = _get_representation(obj, song_schema)
    return jsonify(code=0, result=rep)


@api.route('/add_play', methods=['POST'])
def add_play():
    j = request.get_json(force=True)
    
    # Add to play by song table to query by song
    dsz = play_by_song_schema.load(j)
    _format_errors(dsz.errors)
    obj = dsz.data
    obj.save()
    
    # Add to play by channel table
    dsz = play_by_channel_schema.load(j)
    _format_errors(dsz.errors)
    obj = dsz.data
    obj.save()
    
    # Make sure that the song is inserted in the database
    performer = Song(title=obj.title, performer=obj.performer)
    performer.save()
    
    rep = _get_representation(obj, play_by_channel_schema)
    return jsonify(code=0, result=rep)


@api.route('/get_song_plays', methods=['GET'])
def get_song_plays():
    params = _get_request_parameters(
        required=('title', 'performer', 'start')
    )
    
    q = PlayBySong.objects.filter(
        title=params['title'],
        performer=params['performer'],
        start__gte=params['start'],
        start__lte=params['end']
    )
    
    # Serialize query results
    objs = [play_by_song_schema.dump(o).data for o in q]
    
    return jsonify(code=0, result=objs)


@api.route('/get_channel_plays', methods=['GET'])
def get_channel_plays():
    params = _get_request_parameters(
        required=('channel', 'start')
    )
    
    q = PlayByChannel.objects.filter(
        channel=params['channel'],
        start__gte=params['start'],
        start__lte=params['end']
    )
    
    # Serialize query results
    objs = [play_by_channel_schema.dump(o).data for o in q]
    
    return jsonify(code=0, result=objs)


@api.route('/get_top', methods=['GET'])
def get_top():
    params = _get_request_parameters(
        required=('start')
    )
    
    # Channels is a special parameter that comes in form of a json list
    ds = channels_param_schema.loads(
        '{"channels": %s}' % request.args.get('channels', u'[]')
    )
    _format_errors(ds.errors)
    params['channels'] = ds.data
    
    # TODO: get current and past ranks in parallel
    current_songs = PlayByChannel.get_song_counts(
        params['channels'],
        params['start'],
        params['end']
    )
    
    past_songs = PlayByChannel.get_song_counts(
        params['channels'],
        params['start'] - timedelta(days=7),
        params['end'] - timedelta(days=7)
    )
    
    current_top = topk.fa(current_songs, params['limit'])
    past_top = topk.fa(past_songs, params['limit'])
    
    # Convert to dictionary for fast access
    current_top_dict = {
        item[0]: {
            'rank': i,
            'title': item[0][0],
            'performer': item[0][1],
            'plays': item[1],
            'previous_plays': 0,
            'previous_rank': None
        } for i, item in enumerate(current_top)
    }
    
    past_top_dict = {
        item[0]: {
            'rank': i,
            'plays': item[1]
        } for i, item in enumerate(past_top)
    }
    
    # Merge with previous week
    shared_items = set(past_top_dict.keys()).intersection(current_top_dict.keys()) 
    for item in shared_items:
        current_top_dict[item]['previous_rank'] = past_top_dict[item]['rank']
        current_top_dict[item]['previous_plays'] = past_top_dict[item]['plays']
    
    # Sort and return
    top = sorted(current_top_dict.values(), key=lambda x: x['rank'])
    return jsonify(code=0, result=top)


@api.route('/truncate_tables', methods=['POST'])
def truncate_tables():
    j = request.get_json()

    if 'truncate' not in j:
        raise PlaysException(code=400, errors=['Security flag not present'])
    elif not j['truncate']:
        raise PlaysException(code=400, errors=['Security flag is not set to true'])
    
    _recreate_keyspace()
    
    return jsonify(code=0, result=None)
        
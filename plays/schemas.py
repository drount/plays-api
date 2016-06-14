# -*- coding: utf-8 -*-
from datetime import timedelta
from marshmallow import fields, post_load

from . import ma
from .models import Channel, Performer, Song, PlayByChannel, PlayBySong

class PlaysBaseSchema(ma.Schema):
    
    @post_load
    def make(self, data):
        if self.Meta.model:
            return self.Meta.model(**data)
        else:
            return None
    
    class Meta:
        model = None


class ChannelSchema(PlaysBaseSchema):
    name = fields.String(required=True)

    class Meta:
        model = Channel
        fields = ('name',)


class PerformerSchema(PlaysBaseSchema):
    name = fields.String(required=True)

    class Meta:
        model = Performer
        fields = ('name',)


class SongSchema(PlaysBaseSchema):
    title = fields.String(required=True)
    performer = fields.String(required=True)

    class Meta:
        model = Song
        fields = ('title', 'performer')


class PlaySchema(PlaysBaseSchema):
    title = fields.String(required=True)
    performer = fields.String(required=True)
    start = fields.DateTime(required=True)
    end = fields.DateTime(required=True)
    channel = fields.String(required=True)


class PlayByChannelSchema(PlaySchema):
    class Meta:
        model = PlayByChannel
        fields = ('channel', 'start', 'end', 'title', 'performer')
        

class PlayBySongSchema(PlaySchema):
    class Meta:
        model = PlayBySong
        fields = ('title', 'performer', 'start', 'end', 'channel')


class GetRequestSchema(ma.Schema):
    title = fields.Str(required=True)
    performer = fields.Str(required=True)
    channel = fields.Str(required=True)
    start = fields.DateTime(required=True)
    end = fields.DateTime()
    limit = fields.Integer()
    
    @post_load
    def make(self, data):
        if 'end' not in data:
            data['end'] = data['start'] + timedelta(days=7)
        if 'limit' not in data:
            data['limit'] = 40
        return data
    
    def load(self, data, many=None, partial=None, required=None):
        # Foir the sake of clarity, allow to specify which fields are required
        # instead of the ones that are not
        if required:
            fld = set(GetRequestSchema.Meta.fields)
            req = set(required)            
            partial = fld.difference(req)
            
        return super(GetRequestSchema, self).load(data=data, many=many, partial=partial)
    
    class Meta:
        fields = ('title', 'performer', 'channel', 'start', 'end', 'limit')


class ChannelsParameterSchema(ma.Schema):
    channels = fields.List(fields.Str(), required=True)

    @post_load
    def make(self, data):
        return data['channels']

    class Meta:
        fields = ('channels', )
    


channel_schema = ChannelSchema()
performer_schema = PerformerSchema()
song_schema = SongSchema()
play_by_channel_schema = PlayByChannelSchema()
play_by_song_schema = PlayBySongSchema()
request_schema = GetRequestSchema()
channels_param_schema = ChannelsParameterSchema()
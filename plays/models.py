# -*- coding: utf-8 -*-
import json
import logging

from cassandra.cqlengine import columns
from cassandra.cqlengine.models import Model
from cassandra.cqlengine.management import create_keyspace_simple, sync_table, drop_table

from .db import cluster, session

logger = logging.getLogger()


class Channel(Model):
    name = columns.Text(primary_key=True)

    def __repr__(self):
        return '<Channel(name={self.name!r})>'.format(self=self)


class Performer(Model):
    name = columns.Text(primary_key=True)

    def __repr__(self):
        return '<Performer(name={self.name!r})>'.format(self=self)


class Song(Model):
    title = columns.Text(primary_key=True)
    performer = columns.Text(primary_key=True)

    def __repr__(self):
        return '<Song(title={self.title!r})>'.format(self=self)


class PlayByChannel(Model):
    channel = columns.Text(partition_key=True)
    start = columns.DateTime(primary_key=True)
    end = columns.DateTime()

    title = columns.Text()
    performer = columns.Text()

    def __repr__(self):
        return '<PlayByChannel(channel={self.channel!r})>'.format(self=self)


    song_counts_stmt = None
    
    def __init__(self, *args, **kwargs):
        super(PlayByChannel, self).__init__(*args, **kwargs)
        if not PlayByChannel.song_counts_stmt:
            PlayByChannel.song_counts_stmt = session.prepare(
                """
                SELECT
                    group_and_count(title, performer) as counts 
                FROM
                    play_by_channel
                WHERE
                    channel=? 
                    AND
                    start>=?
                    AND
                    start <=?
                """
            )

    @staticmethod
    def get_song_counts(channels, start, end):
        # TODO: Limit songs by count threshold
        # Launch async queries for every channel
        futures = []
        for channel in channels:
            future = session.execute_async(
                PlayByChannel.song_counts_stmt,
                [channel, start, end]
            )
            futures.append((channel, future))


        counts = {}
        for channel, future in futures:
            # Block until result is set
            q = future.result()

            if len(q.current_rows) == 0:
                continue

            # Sort song counts descending
            channel_counts = {}
            for key, value in q[0].counts.items():
                l_key = json.loads(key)
                # Convert title and performer to tuple
                channel_counts[(l_key[0], l_key[1])] = value

            counts[channel] = channel_counts

        return counts


class PlayBySong(Model):
    title = columns.Text(partition_key=True)
    performer = columns.Text(partition_key=True)
    start = columns.DateTime(primary_key=True)
    end = columns.DateTime()

    channel = columns.Text()

    def __repr__(self):
        return '<PlayBySong(title={self.title!r})>'.format(self=self)


def _sync_database():
    logger.info("Synching Tables")
    sync_table(Channel)
    sync_table(Performer)
    sync_table(Song)
    sync_table(PlayByChannel)
    sync_table(PlayBySong)

    logger.info("Finished")


def _recreate_keyspace():
    logger.info("Dropping tables")
    drop_table(Channel)
    drop_table(Performer)
    drop_table(Song)
    drop_table(PlayByChannel)
    drop_table(PlayBySong)
    
    _sync_database()
    
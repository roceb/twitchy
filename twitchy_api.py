#!/usr/bin/env python3
# Twitch API interaction module

import ast
import datetime

import twitchy_database
from twitchy_config import YouAndTheHorseYouRodeInOn

try:
    import requests
except ImportError:
    raise YouAndTheHorseYouRodeInOn(' requests not installed.')

from pprint import pprint


def api_call(url, params=None):
    try:
        headers = {
            'Client-ID': 'guulhcvqo9djhuyhb2vi56wqnglc351'}

        r = requests.get(
            url,
            headers=headers,
            params=params)

        return r.json()

    except requests.exceptions.ConnectionError:
        raise YouAndTheHorseYouRodeInOn(' Unable to connect to Twitch.')


def name_id_translate(data_type, mode, data):
    # data is expected to be a list
    # data_type is either 'games' or 'channels'

    # All API calls are now based on the presence of
    # an id field. This needs to be derived first

    # The new API also returns the display_name value here
    # in case of channel names
    # This will have to be cached in the database

    # Returns a dictionary

    # Set the default value for params
    # This is for 'name_from_id'
    # for either data_type
    params = (('id', data),)

    if data_type == 'games':
        api_endpoint = 'https://api.twitch.tv/helix/games'
        if mode == 'id_from_name':
            params = (('name', data),)

    elif data_type == 'channels':
        api_endpoint = 'https://api.twitch.tv/helix/users'
        if mode == 'id_from_name':
            channels = [i[0].lower() for i in data]
            params = (('login', channels),)

    stream_data = api_call(
        api_endpoint,
        params)

    if data_type == 'channels':
        return_dict = {}

        for i in stream_data['data']:
            channel_params = {
                'id': i['id'],
                'broadcaster_type': i['broadcaster_type'],
                'display_name': i['display_name']}

            return_dict[i['login']] = channel_params

        return return_dict

    if data_type == 'games':
        return_list = []

        for i in stream_data['data']:
            game_params = {
                'id': i['id'],
                'name': i['name']}

            return_list.append(
                [game_params['id'], game_params['name']])

        return return_list


def sync_from_id(username):
    # username is expected to be a string in lowecase
    # Make sure this is set in the initiating function
    # Example: sync_from_id('<username>')

    username_id = get_users('id_from_name', [username.lower()])
    if username_id:
        print(username_id)
        username_id = username_id[username]['id']
    else:
        # In case no id is returned by get_idget_users
        return

    # TODO
    # The results_expected has to pushed up to 100
    # This will involve passing a 'first' param
    followed_channels_ids = []
    params = (('from_id', username_id),)
    while True:
        results_expected = 20
        api_endpoint = 'https://api.twitch.tv/helix/users/follows'

        stream_data = api_call(
            api_endpoint,
            params)

        for i in stream_data['data']:
            followed_channels_ids.append(
                int(i['to_id']))

        results_acquired = len(stream_data['data'])
        if results_acquired < results_expected:
            break
        else:
            params = (
                ('from_id', username_id),
                ('after', stream_data['pagination']['cursor']))

    # At this point, followed_channels_ids is a list containing the
    # user ids of the channels the user follows
    # This will have to be converted into a more detailed dictionary

    followed_channels = get_users('name_from_id', followed_channels_ids)
    return followed_channels


class GetOnlineStatus:
    def __init__(self, channels):
        # Again, channels is expected to be a tuple
        # containing the _id as a string
        # More than 100 channels will be paginated
        # Example:
        # channels = GetOnlineStatus(['22588033', '26610234'])
        # channels.check_channels()
        # print(channels.online_channels)
        self.channels = channels
        self.online_channels = {}

    def parse_uptime(self, start_time):
        # Uptime is returned in seconds
        # We'll be using twitchy_display.time_convert()
        # to... convert this into what will be
        # displayed according to the sort order
        datetime_start_time = datetime.datetime.strptime(
            start_time,
            '%Y-%m-%dT%H:%M:%SZ')
        stream_uptime_seconds = (
            datetime.datetime.utcnow() -
            datetime_start_time).seconds

        return stream_uptime_seconds

    def get_game(self, game_id):
        # The game_id is expected to be an integer
        # The idea is to check the database for said integer
        # and return data accordingly
        # If nothing is found, create a new entry within the database
        # and put them newly discovered details here
        # Whoever thought of 2 endpoints for this
        # can walk on broken glass
        try:
            game_name = twitchy_database.DatabaseFunctions().fetch_data(
                ('Name', 'AltName'),
                'games',
                {'GameID': game_id},
                'EQUALS')[0]
            return game_name
        except TypeError:
            # Implies the game is not in the database
            # Its name will have to be fetched from the API
            # Fuck whoever thought of this
            game_details = name_id_translate('games', 'name_from_id', (game_id,))
            return (game_details[0][1], None)

    def check_channels(self):
        # The API imposes an upper limit of 100 channels
        # checked at once. Pagination is required, as usual.
        while self.channels:
            api_endpoint = 'https://api.twitch.tv/helix/streams'

            params = (
                ('first', 100),
                ('user_id', self.channels[:100]))

            del self.channels[:100]
            stream_data = api_call(
                api_endpoint,
                params)

            # The API currently does NOT return the game_name
            # It does return a game_id. In case you intend to go
            # forward with that at this time, the game_id will have
            # to be cached in the database along with its name

            # The stream data dictionary is
            # Key: name
            # Value: as below
            # Partner status will have to come from another endpoint
            # Time watched is a database function - See if it
            # needs to be integrated here

            for i in stream_data['data']:

                user_id = i['user_id']
                channel_details = twitchy_database.DatabaseFunctions().fetch_data(
                    ('Name', 'DisplayName', 'AltName', 'IsPartner'),
                    'channels',
                    {'ChannelID': user_id},
                    'EQUALS')[0]

                channel_name = channel_details[0]

                # Set the display name to a preset AltName if possible
                # Or go back to the display name set by the channel
                channel_display_name = channel_details[2]
                if not channel_display_name:
                    channel_display_name = channel_details[1]

                # Partner status is returned as string True
                # This is clearly unacceptable for anyone who
                # doesn't sleep in a dumpster
                is_partner = ast.literal_eval(channel_details[3])

                uptime = self.parse_uptime(i['started_at'])

                # Game name and any alternate names will have to be correlated
                # to the game_id that's returned by the API
                # Whoever thought this was a good idea can sit on it and rotate

                game_id = i['game_id']
                game_names = self.get_game(game_id)
                game_display_name = game_names[0]
                if game_names[1]:
                    game_display_name = game_names[1]

                self.online_channels[channel_name] = {
                    'game_id': game_id,
                    'game_display_name': game_display_name,
                    'status': i['title'],
                    'viewers': i['viewer_count'],
                    'display_name': channel_display_name,
                    'uptime': uptime,
                    'is_partner': is_partner}

        return self.online_channels

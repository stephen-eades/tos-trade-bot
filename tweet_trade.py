"""TOS-Trade-Bot docstrings

This module provides functions and classes that can be called on a 
reoccurring basis to send a Tweet for each stock trade that occurs.
Additionally will Tweet current positions at the beginning of each day.
This is built for TD Ameritrade's API, but could be easily repurposed.
A Twitter developer account and TD Ameritrade account are required.
"""

import requests
import json
import tweepy
import sys 
from os import environ
from datetime import datetime, timedelta


"""Heroku Variables

Input these values in your Heroku account.
Look in the settings under the Config Vars section.
Comment these out when testing with local variables below.
"""
env_client_id = environ['CLIENT_ID']
env_account_id = environ['ACCOUNT_ID']
env_redirect_uri = environ['REDIRECT_URI']
env_code = environ['CODE']
env_refresh_token = environ['REFRESH_TOKEN']
env_twitter_key = environ['TWITTER_KEY']
env_twitter_secret_key = environ['TWITTER_SECRET_KEY']
env_twitter_token = environ['TWITTER_TOKEN']
env_twitter_secret_token = environ['TWITTER_SECRET_TOKEN']


"""Test Variables

Enter your own variables for local testing.
Make sure to delete these values if you plan to commit this.
"""
test_client_id = ''
test_account_id = ''
test_redirect_uri = ''
test_code = ''
test_refresh_token = ''
test_twitter_key = ''
test_twitter_secret_key = ''
test_twitter_token = ''
test_twitter_secret_token = ''


def get_access_token(client_id, redirect_uri, refresh_token, code):
    """Authenticate with TD Ameritrade's API to get an access token."""

    if refresh_token:
        # Our refresh token is available
        try:
            return authenticate_with_refresh_token(client_id, redirect_uri, refresh_token)
        except:
            print('Unable to authenticate using refresh token.')
            return ''
    elif code:
        # Refresh token was empty, try the code
        try:
            return authenticate_with_code(client_id, redirect_uri, code)
        except: 
            print('Unable to authenticate using code.')
            return ''
    else:
        # Exception occurred
        print('Error occurred. Check refresh token and Heroku logs for stack trace: `heroku logs -t`.')
        return ''


def authenticate_with_refresh_token(client_id, redirect_uri, refresh_token):
    """Get an access token with the existing refresh token."""

    try:
        url = 'https://api.tdameritrade.com/v1/oauth2/token'
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        payload='grant_type=refresh_token&refresh_token='+refresh_token+'&client_id='+client_id+'&redirect_uri='+redirect_uri
        response = requests.request("POST", url, headers=headers, data = payload)
        data = response.json()
        return data['access_token']
    except:
        # Exception occurred, refresh token is invalid
        print('Invalid refresh token.')
        return ''


def authenticate_with_code(client_id, redirect_uri, code):
    """Get an access token with a new code."""

    try:
        url = 'https://api.tdameritrade.com/v1/oauth2/token'
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        payload='code='+code+'&grant_type=authorization_code&access_type=offline&redirect_uri='+redirect_uri+'&client_id='+client_id
        response = requests.request("POST", url, headers=headers, data=payload)
        data = response.json()
        refresh_token = data['refresh_token']
        return data['access_token']
    except: 
        # Exception occurred, code is invalid
        print('Invalid code.')
        return ''


class Tweet(object):
    """Create a Tweet object that will be used for each trade that needs Tweeted."""

    quantity = ""
    ticker = ""
    asset_description = ""
    price = ""
    tx_date = ""
    tx_time = ""
    instrument = ""
    trade_type = ""

    def __init__(self, quantity, ticker, asset_description, price, tx_date, tx_time, instrument, trade_type):
        self.quantity = str(quantity)
        self.ticker = ticker
        self.asset_description = asset_description
        self.price = str(price)
        self.tx_date = str(tx_date)
        self.tx_time = str(tx_time)
        self.instrument = instrument
        self.trade_type = trade_type


def make_tweet(quantity, ticker, asset_description, price, tx_date, tx_time, instrument, trade_type):
    """Create and return a new instance of a Tweet object."""

    tweet = Tweet(quantity, ticker, asset_description, price, tx_date, tx_time, instrument, trade_type)
    return tweet


def check_for_recent_trades(account_id, access_token):
    """Check for trade activity from the previous day and return it as json data."""
    
    # Get the account's recent activity for the previous day
    url = 'https://api.tdameritrade.com/v1/accounts/' + account_id + '/transactions'
    headers = {
        'Authorization': 'Bearer '+ access_token,
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    params = {'type':'TRADE', 'startDate':(datetime.now() - timedelta(1)).strftime('%Y-%m-%d')}
    payload = {}
    response = requests.request("GET", url, headers=headers, params=params, data=payload)
    data = response.json()
    return data


def create_tweet_list(data):
    """Take the most recent trades and return a list of Tweet objects"""

    now = datetime.now()
    tweet_list = []
    for x in range(len(data)): 
        
        try:
            transaction_date_string = data[x]['transactionDate']
            transaction_datetime_object = datetime.strptime(transaction_date_string, '%Y-%m-%dT%H:%M:%S+0000').replace(microsecond=0)
            if now-timedelta(hours=24) <= transaction_datetime_object <= now: 
                # If trades are detected, take necessary data from them
                if data[x]['transactionItem']['instrument']['assetType'] == 'EQUITY':
                    # For equity instruments
                    quantity = data[x]['transactionItem']['amount']
                    ticker = data[x]['transactionItem']['instrument']['symbol']
                    asset_description = 'SHARES'
                    price = data[x]['transactionItem']['price']
                    tx_date = data[x]['transactionDate'].split('T')[0]
                    tx_time = data[x]['transactionDate'].split('T')[1]
                    instrument = "EQUITY"
                    trade_type = data[x]['description']

                elif data[x]['transactionItem']['instrument']['assetType'] == 'OPTION':
                    # For option instruments
                    quantity = data[x]['transactionItem']['amount']
                    ticker = data[x]['transactionItem']['instrument']['underlyingSymbol']
                    asset_description = data[x]['transactionItem']['instrument']['description']
                    price = data[x]['transactionItem']['price']
                    tx_date = data[x]['transactionDate'].split('T')[0]
                    tx_time = data[x]['transactionDate'].split('T')[1]
                    instrument = "OPTION"
                    trade_type = data[x]['description']

                # Format data into tweet and prepare to print it
                trade_tweet = make_tweet(quantity, ticker, asset_description, price, tx_date, tx_time, instrument, trade_type)
                tweet_list.append(trade_tweet)
        except:
            # no trades found
            print('No trades detected')
            pass

    return tweet_list


def send_tweets(list_of_tweets, key, secret_key, token, secret_token):
    """Take the list of trades from the previous day and post them to the Twitter account after auth"""

    # Authorize with the Twitter API
    auth = tweepy.OAuthHandler(key, secret_key)
    auth.set_access_token(token, secret_token)
    api = tweepy.API(auth)
    plus_minus_sign = ""

    for tweet in list_of_tweets:
        # Determine is buying or selling
        if tweet.trade_type == "BUY TRADE":
            plus_minus_sign = "+"
        else:
            plus_minus_sign = "-"

        # Check if the ticker already exists on the timeline
        reply_tweet_id = check_timeline_for_ticker(tweet.ticker, api)

        # Determine if Equity or Option
        if tweet.instrument == "EQUITY":
            if (reply_tweet_id):
                api.update_status(
                    "-----TRADE ALERT----- \n" 
                    + plus_minus_sign + tweet.quantity +' $'+ tweet.ticker + ' SHARES \n' 
                    + '-------------------------------- \n' 
                    + 'Price: $' + tweet.price +'\n' 
                    + 'Timestamp: ' + tweet.tx_date+'@'+tweet.tx_time+'\n'
                    +'--------------------------------', reply_tweet_id)
            else:
                api.update_status(
                    "-----TRADE ALERT----- \n" 
                    + plus_minus_sign + tweet.quantity +' $'+ tweet.ticker + ' SHARES \n' 
                    + '-------------------------------- \n' 
                    + 'Price: $' + tweet.price +'\n' 
                    + 'Timestamp: ' + tweet.tx_date+'@'+tweet.tx_time+'\n'
                    +'--------------------------------')

        elif tweet.instrument == "OPTION":
            if (reply_tweet_id):
                api.update_status(
                    "-----TRADE ALERT----- \n" 
                    + plus_minus_sign + tweet.quantity +' $'+ tweet.asset_description+ '\n' 
                    + '-------------------------------- \n' 
                    + 'Price: $' + tweet.price +'\n' 
                    + 'Timestamp: ' + tweet.tx_date+'@'+tweet.tx_time+'\n'
                    +'--------------------------------', reply_tweet_id)
            else:
                api.update_status(
                    "-----TRADE ALERT----- \n" 
                    + plus_minus_sign + tweet.quantity +' $'+ tweet.asset_description+ '\n' 
                    + '-------------------------------- \n' 
                    + 'Price: $' + tweet.price +'\n' 
                    + 'Timestamp: ' + tweet.tx_date+'@'+tweet.tx_time+'\n'
                    +'--------------------------------')

        else:
            # add new instrument types here
            pass


def check_timeline_for_ticker(ticker, api):
    """Check if there are any Tweets with the ticker on the timeline"""

    for status in tweepy.Cursor(api.user_timeline, screen_name='@stephens_log', tweet_mode="extended").items():
        if str('$'+ticker) in status.full_text and 'POSITION ALERT' not in status.full_text:
            # Return the first, most recent instance of the tweet with that ticker
            return status.id


def check_for_positions(account_id, access_token):
    """Check for current positions and return them as json data."""
    
    # Get the account's current positions
    url = 'https://api.tdameritrade.com/v1/accounts/' + account_id
    headers = {
        'Authorization': 'Bearer '+ access_token,
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    params = {'fields':'positions'}
    payload = {}
    response = requests.request("GET", url, headers=headers, params=params, data=payload)
    data = response.json()
    return data    


def create_position_ticker_list(data):
    """Take the current position data and create list of tickers"""

    ticker_list = []
    try:
        for x in range(len(data['securitiesAccount']['positions'])):
            # If any positions are detected, take necessary data from them
            ticker = data['securitiesAccount']['positions'][x]['instrument']['symbol'].split('_')[0]
            # Do a check here to make sure tickers are not duplicated
            if ticker not in ticker_list:
                ticker_list.append(ticker)

    except:
        # no positions found
        print('No positions detected')
        ticker_list = ['No active positions']
        pass

    return ticker_list  


def prepend_dollar_sign_to_ticker(list, str):
    """Add a dollar sign character to the beginning of each ticker in the list"""    

    str += '{0}'
    list = [str.format(i) for i in list] 
    return(list)     


def send_position_tweet(ticker_list, key, secret_key, token, secret_token):
    """Take the position ticker list and post to the Twitter account after auth"""

    # Authorize with the Twitter API
    auth = tweepy.OAuthHandler(key, secret_key)
    auth.set_access_token(token, secret_token)
    api = tweepy.API(auth)

    if ticker_list:
        tickers_list_with_dollar_sign = prepend_dollar_sign_to_ticker(ticker_list, '$')
        tickers_string = " "
        tickers_string = tickers_string.join(tickers_list_with_dollar_sign)
    else:
        tickers_string = tickers_string.join(ticker_list)

    api.update_status(
        "-----POSITION ALERT----- \n" 
        + 'Premarket Current Positions \n' 
        + '-------------------------------- \n' 
        + tickers_string + '\n'
        +'--------------------------------')


def tweet_trades_from_prior_day():
    """Main flow for checking recent trades and posting them to Twitter. Runs on schedule in clock.py"""

    access_token = get_access_token(env_client_id, env_redirect_uri, env_refresh_token, env_code)
    trade_data = check_for_recent_trades(env_account_id, access_token)
    prepared_tweets = create_tweet_list(trade_data)
    send_tweets(prepared_tweets, env_twitter_key, env_twitter_secret_key, env_twitter_token, env_twitter_secret_token)


def tweet_positions():
    """Main flow for current positions and posting them to Twitter. Runs on schedule in clock.py"""

    access_token = get_access_token(env_client_id, env_redirect_uri, env_refresh_token, env_code)
    position_data = check_for_positions(env_account_id, access_token)
    ticker_list = create_position_ticker_list(position_data)
    send_position_tweet(ticker_list, env_twitter_key, env_twitter_secret_key, env_twitter_token, env_twitter_secret_token)



# Use this for testing transactions locally
# access_token = get_access_token(test_client_id, test_redirect_uri, test_refresh_token, test_code)
# print(access_token[0:10])
# trade_data = check_for_recent_trades(test_account_id, access_token)
# prepared_tweets = create_tweet_list(trade_data)
# print(prepared_tweets)
# send_tweets(prepared_tweets, test_twitter_key, test_twitter_secret_key, test_twitter_token, test_twitter_secret_token)

# Use this for testing positions locally
# access_token = get_access_token(test_client_id, test_redirect_uri, test_refresh_token, test_code)
# print(access_token[0:10])
# position_data = check_for_positions(test_account_id, access_token)
# ticker_list = create_position_ticker_list(position_data)
# print(ticker_list)
# send_position_tweet(ticker_list, test_twitter_key, test_twitter_secret_key, test_twitter_token, test_twitter_secret_token)
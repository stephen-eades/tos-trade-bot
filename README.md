# tos-trade-bot
Think or Swim python bot that tweets all my trades from the previous day and my current positions each morning at 6:00am EST.

## Notes
* `access_token` expires after 30 minutes
* `refresh_token` expires after 90 days
* requires manual entry of `refresh_token` every 90 days until persistent auth flow is complete

## TODO
* Change hosting to setup persistent auth flow
* Implement tda streamer service for realtime trade detection
from apscheduler.schedulers.blocking import BlockingScheduler
from tweet_trade import tweet_trades_from_prior_day, tweet_positions

sched = BlockingScheduler()

@sched.scheduled_job('cron', day_of_week='tue-sat', hour='6', minute="00", timezone='America/New_York')
def tweet_trades_from_prior_day_scheduled_job():
    tweet_trades_from_prior_day()

@sched.scheduled_job('cron', day_of_week='mon', hour='5', minute="55", timezone='America/New_York')
def tweet_positions_scheduled_job():
    tweet_positions()

sched.start()
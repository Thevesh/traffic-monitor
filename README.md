This code should help you quickly deploy your own version of a traffic monitor, with output as shown [here](https://thev.cloud/raya-traffic).

Setup requirements:

1) Rename `constants.example` to `constants.py`, which has been added to the gitignore to prevent accidental leakage of secrets (best practice is to use an environment variable, but this will do).

2) `python3 -m venv .venv` and then `pip3 install -r requirements.txt`
   
3) Do the following to complete `constants.py`:
- Create a Google Cloud Platform (GCP) account, enable the Directions API, and add your API key in.
- Create a Telegram bot (visit @BotFather on Telegram) and add the bot's key.
- Create a Telegram channel, add the bot as an admin, and add the channel's ID (use @myidbot to get the ID).

4) Change the chains and locations in `dep/stops.csv` to monitor your own routes.

Deployment:

Not going to be too prescriptive, as most will have their own preference, but the [live use case](https://thev.cloud/raya-traffic) was deployed from a small VM running Ubuntu 22.04 LTS, using crontab. Nothing fancy.

This was the `.sh` script in `~/crons/traffic.sh` (don't forget to `chmod + x ~/crons/traffic.sh`):
```
#!/bin/bash
# activate Python venv and run daily script
source ~/YOUR_GIT_FOLDER_PATH/.venv/bin/activate
cd ~/YOUR_GIT_FOLDER_PATH/
python3 cron_traffic_raya.py
```

And this was the crontab file (amend as desired to reduce/increase frequency, which will correlate to costs):
```
0-59/20 * * * * ~/crons/traffic.sh
```

# Lounge Updating Bot

This is the source code for the bot used to submit/update tables in MK8DX/MK7 Lounge servers, written using Discord.py. Currently it only works with websites based on Vike's [Lounge API](https://github.com/VikeMK/Lounge-API/), however the code can be easily extended to use other APIs in the future.

Features:
- Submitting tables of lounge matches
- Penalties/bonuses
- Creating MMR table images to show MMR gains/losses using matplotlib
- Chat restricting players to only allow them to send a select list of phrases
- Adding/editing player info through the website API
- Logging all reactions used in a server
- Automatically updating player roles depending on their MMR
- Season resets, including a command to import placements from a csv file and fix all roles if MMR thresholds change

# Setup

1) Run `git clone https://github.com/cyndaquilx/Lounge-Updating-Bot`
2) Setup a bot account: https://discord.com/developers/applications/
3) Create a `config.json` file for your lounge server. You can see `sample_config.json` for an example, and `models/Config.py` for a list of fields required for the bot to start up (the `config.json` file must have all of the required fields of dataclass BotConfig)
4) You can either run the bot using a Python virtual environment or using Docker. If you're using Docker, you can run the `sudo ./redeploy.sh` command as a shorthand to rebuild and restart the container.
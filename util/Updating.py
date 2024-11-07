from discord.ext import commands
from models import LeaderboardConfig, Table
import API.get, API.post
from util.Players import place_player_with_mmr_new

def parse_multipliers(args: str):
    # multipliers are separated by comma: ex. Cynda 0.5, Vike 1.0
    mult_args = args.split(",")
    multipliers: dict[str, float] = {}
    for mult in mult_args:
        split_mult = mult.split()
        if len(split_mult) >= 2:
            # the player name is every word of the split multiplier besides the last one,
            # which is the number
            player_name = " ".join(split_mult[:-1]).strip()
            player_mult = split_mult[-1].strip()
            try:
                if float(player_mult) < 0.0 or float(player_mult) > 2.0:
                    errMsg = f"{player_mult} is not a valid multiplier!"
                    return None, errMsg
                multipliers[player_name] = float(player_mult)
            except Exception as e:
                errMsg = f"{player_mult} is not a valid multiplier!"
                return None, errMsg
    return multipliers, None

def parse_scores(args: str):
    # arguments are separated by commas: ex. Cynda 82, Vike 83
    player_scores = args.split(",")
    scores: dict[str, int] = {}
    for score in player_scores:
        split_score = score.split()
        if len(split_score) >= 2:
            # the player name is every word of the split score besides the last one,
            # which is the number
            player_name = " ".join(split_score[:-1]).strip()
            player_score = split_score[-1].strip()
            try:
                if int(player_score) < 12 or int(player_score) > 180:
                    errMsg = f"{player_score} is not a valid score!"
                    return None, errMsg
                scores[player_name] = int(player_score)
            except Exception as e:
                errMsg = f"{player_score} is not a valid score!"
                return None, errMsg
    return scores, None

async def set_multipliers(ctx: commands.Context, lb: LeaderboardConfig, table_id: int, args: str):
    multipliers, error = parse_multipliers(args)
    if multipliers is None:
        await ctx.send(error)
        return False
    if multipliers != {}:
        updatedMultipliers = await API.post.setMultipliers(lb.website_credentials, table_id, multipliers)
        if updatedMultipliers is not True:
            await ctx.send("Error setting multipliers:\n%s"
                            % updatedMultipliers)
            return False
    return True

async def check_placements(ctx: commands.Context, lb: LeaderboardConfig, table: Table):
    for team in table.teams:
        for score in team.scores:
            if score.prev_mmr is None:
                place_mmr = lb.get_place_mmr(score.score)
                await place_player_with_mmr_new(ctx, lb, place_mmr, score.player.name)

import discord
from discord.ext import commands
import functools
from collections.abc import Callable
from typing import Concatenate, ParamSpec

P = ParamSpec("P")

# test, not used
def leaderboard_command(*dec_args, **dec_kwargs):
    def command_decorator(func: Callable[Concatenate[commands.Context, int, P], None]) -> Callable[Concatenate[commands.Context, P], None]:
        @functools.wraps(func)
        async def command_wrapper(ctx: commands.Context, *args: P.args, **kwargs: P.kwargs):
            f = functools.partial(func, num=0)
            await f(ctx, *args, **kwargs)
        return commands.command(*dec_args, **dec_kwargs)(command_wrapper)
    return command_decorator
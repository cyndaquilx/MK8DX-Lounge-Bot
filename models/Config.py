from dataclasses import dataclass

@dataclass
class WebsiteCredentials:
    url: str
    username: str
    password: str

@dataclass
class LeaderboardRank:
    emoji: str
    role_id: int
    color: str
    url: str
    mmr: int

@dataclass
class LeaderboardConfig:
    website_credentials: WebsiteCredentials
    placement_role_id: int
    player_role_id: int
    name_change_log_channel: int
    name_request_log_channel: int
    name_request_channel: int
    updating_log_channel: int
    mute_ban_list_channel: int
    quick_start_channel: int
    ranks: dict[str, LeaderboardRank]
    tier_results_channels: dict[str, int]
    place_rank_mmrs: dict[str, int]
    place_scores: dict[int, int]

    def get_rank(self, mmr:int):
        # get all the ranks where our MMR is higher than the minimum MMR
        valid_ranks = [r for r in self.ranks.values() if r.mmr <= mmr]
        # get the highest mmr of those ranks
        rank = max(valid_ranks, key=lambda r: r.mmr)
        return rank

@dataclass
class ServerConfig:
    prefixes: dict[str, str]
    reporter_roles: list[int]
    staff_roles: list[int]
    admin_roles: list[int]
    mkc_roles: list[int]
    chat_restricted_roles: list[int]
    name_restricted_roles: list[int]
    tier_channel_categories: list[int]
    leaderboards: dict[str, LeaderboardConfig]

@dataclass
class BotConfig:
    token: str
    application_id: int
    servers: dict[int, ServerConfig]
    
    def get_prefixes(self):
        prefixes = []
        for server in self.servers.values():
            for prefix in server.prefixes:
                if prefix == "":
                    prefixes.append("!")
                else:
                    prefixes.append(f"!{prefix} ")
        prefixes = list(set(prefixes))
        prefixes.sort(key=len, reverse=True) # sort in descending order of length to ensure all can be used
        return prefixes
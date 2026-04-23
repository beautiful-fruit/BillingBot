from discord import TextChannel

from re import findall


def post_filter(
    channel: TextChannel,
    message: str
) -> str:
    members = channel.members
    members_id_map = {
        str(member.id): member
        for member in members
    }

    mention_ids = findall(r"<@!?(\d+)>", message)
    if len(mention_ids) >= 5:
        for mention_id in mention_ids:
            message = message.replace(
                f"<@{mention_id}>",
                members_id_map[mention_id].display_name
                if mention_id in members_id_map
                else f"<{mention_id}>"
            )
            message = message.replace(
                f"<@!{mention_id}>",
                members_id_map[mention_id].display_name
                if mention_id in members_id_map
                else f"<{mention_id}>"
            )

    return message

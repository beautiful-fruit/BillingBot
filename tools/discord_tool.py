from discord import Member, Role, User, TextChannel

from typing import Annotated, Union

from .base import ToolBase


class DiscordTools(ToolBase):
    class_name = "discord"


def user_to_dict(user: Union[User, Member]) -> dict:
    return {
        "id": str(user.id),
        "username": user.name,
        "display_name": user.display_name,
        "joined_at": str(user.joined_at) if isinstance(user, Member) else None,
    }


def role_to_dict(role: Role) -> dict:
    return {
        "id": str(role.id),
        "name": role.name,
        "color": role.color.value,
    }


@DiscordTools.register("獲取當前頻道的所有使用者列表")
async def get_channel_members(
    channel: TextChannel
) -> list[dict]:
    members = channel.members
    member_list = [
        {
            "id": str(member.id),
            "username": member.name,
            "name": member.display_name,
        }
        for member in members
    ]
    return member_list


@DiscordTools.register("通過使用者 ID 獲取使用者資料")
async def get_user_by_id(
    user_id: Annotated[str, "Discord 使用者 ID"],
    channel: TextChannel
) -> dict:
    member = channel.guild.get_member(int(user_id))
    if member is None:
        return {}

    return {
        **user_to_dict(member),
        "roles": [
            role_to_dict(role)
            for role in member.roles
        ]
    }


@DiscordTools.register("通過身分組 ID 獲取身分組資料")
async def get_role_by_id(
    role_id: Annotated[str, "Discord 身分組 ID"],
    channel: TextChannel
) -> dict:
    role = channel.guild.get_role(int(role_id))
    if role is None:
        return {}

    return {
        **role_to_dict(role),
        "members": [
            user_to_dict(member)
            for member in role.members
        ]
    }

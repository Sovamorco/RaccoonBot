from credentials import discord_message_id, discord_channel_id, discord_guild_id, emoji_to_role


async def check(bot):
    guild = bot.get_guild(discord_guild_id)
    channel = guild.get_channel(discord_channel_id)
    message = await channel.fetch_message(discord_message_id)
    reactions = message.reactions
    for reaction in reactions:
        users = await reaction.users().flatten()
        role = guild.get_role(emoji_to_role[reaction.emoji.name])
        for member in guild.members:
            if not member.bot:
                if member in users and role not in member.roles:
                    await member.add_roles(role)
                elif member not in users and role in member.roles:
                    await member.remove_roles(role)

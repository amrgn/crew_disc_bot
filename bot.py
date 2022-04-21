import os
from dotenv import load_dotenv
from discord.ext import commands
import datetime

import asyncio

import discord

from util import *

class CustomBot(commands.Bot):
    def __init__(self, reactions, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reactions: ReactionEmojis = reactions
        self.delay_cmd: DelayCmd = DelayCmd()

class DelayCmd:
    """
    Implements a command delay queue system to avoid hitting discord rate limit (call delay on a shared DelayCmd object before executing a command)
    """
    def __init__(self):
        self.curr_cmd = 0
        self.total_cmd = 0

        self.lock = asyncio.Lock()

    async def delay(self):
        async with self.lock:
            local_cmd = self.total_cmd
            self.total_cmd += 1
        
        while self.curr_cmd != local_cmd:
            await asyncio.sleep(0.1)
        
        await asyncio.sleep(1)

        async with self.lock:
            self.curr_cmd += 1

            if self.curr_cmd == self.total_cmd: # no commands in queue at the moment, so reset values. Not strictly necessary
                self.curr_cmd = 0
                self.total_cmd = 0

        return



class ReactionEmojis:
    """
    Holds reactions to be applied to messages for each user
    """
    MAX_DURATION = 14

    def __init__(self):
        self.reactions = {}
    
    def add_reaction(self, usr_id: int, emoji: str, duration: int):
        self.remove_old_reactions()

        if duration > ReactionEmojis.MAX_DURATION or duration < 0:
            raise ValueError("Invalid duration")

        if usr_id not in self.reactions:
            self.reactions[usr_id] = {}
        
        self.reactions[usr_id][emoji] = datetime.datetime.now() + datetime.timedelta(days=duration)

    
    def remove_old_reactions(self):
        curr_time = datetime.datetime.now()
        for usr_id in self.reactions:
            fix_usr_emojis = False
            for emoji in self.reactions[usr_id]:
                if self.reactions[usr_id][emoji] < curr_time:
                    self.reactions[usr_id][emoji] = None
                    fix_usr_emojis = True
            
            if fix_usr_emojis:
                self.reactions[usr_id] = {emoji: datetime_obj for emoji, datetime_obj in self.reactions[usr_id].items() if datetime_obj is not None}
    
    def get_reactions(self, usr_id):
        self.remove_old_reactions()

        if usr_id not in self.reactions:
            return []
        else:
            return list(self.reactions[usr_id])

def get_token():
    load_dotenv()
    return os.getenv("DISCORD_TOKEN")

def get_client():
    intents = discord.Intents.default()
    intents.messages = True
    intents.members = True

    client = CustomBot(ReactionEmojis(), command_prefix="!", intents=intents)

    @client.event
    async def on_ready():
        print(f'Logged in as {client.user} (ID: {client.user.id})')
        print('------')

    @client.event
    async def on_message(message):
        usr_id = message.author.id

        emojis = client.reactions.get_reactions(usr_id)

        for emoji in emojis:
            try:
                await client.delay_cmd.delay()
                await message.add_reaction(emoji)
            except discord.NotFound:
                pass
            except discord.HTTPException:
                pass


        await client.process_commands(message)


    @client.command()
    async def react(ctx, usr: str, reaction: str, duration: int = 3):
        """Adds reaction for user"""
        print(f"Client {client.user} issued command to add reaction {reaction} for user {usr} for {duration} days")
        
        usr_id = get_id_from_tag(usr)

        if usr_id is None:
            await client.delay_cmd.delay()
            await ctx.send(f"Error, unable to find user {usr}. Use the tagged user as the first argument to this command. Example usage: !react <@966146137662820463> 😄 3")
            return
        
        if usr_id == ctx.author.id:
            await client.delay_cmd.delay()
            await ctx.send(f"Nice try, dumbass. You can't issue reactions for yourself.")
            return

        try:
            client.reactions.add_reaction(usr_id, reaction, duration)
            await client.delay_cmd.delay()
            await ctx.send(f"Added reaction {reaction} for user {usr} for {duration} days")
        except ValueError:
            await client.delay_cmd.delay()
            await ctx.send(f"Invalid duration. Duration must be a value between 0 and 14 (days).")
            

    return client

def main():
    
    TOKEN = get_token()
    client = get_client()
    
    client.run(TOKEN)



if __name__ == "__main__":
    main()
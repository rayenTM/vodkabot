import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
import os
import time

# Database file path
DB_FILE = "/app/data/levels.db" if os.path.exists("/app/data") else "./data/levels.db"

class Levels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = None
        self.cooldowns = {} # user_id -> timestamp

    def get_xp_for_next_level(self, current_level: int) -> int:
        """
        Quadratic Formula: 5 * (L^2) + 50 * L + 100
        L=1 -> 155
        L=2 -> 220
        L=10 -> 1100
        """
        return 5 * (current_level ** 2) + 50 * current_level + 100

    def get_total_xp_for_level(self, target_level: int) -> int:
        """Sum of XP needed for all levels up to target_level - 1"""
        total = 0
        for i in range(1, target_level):
            total += self.get_xp_for_next_level(i)
        return total

    # --- Public Admin Methods (API) ---

    async def admin_give_xp(self, user_id: int, guild_id: int, amount: int):
        """Adds (or removes) XP and returns the new total XP."""
        await self.db.execute("""
            INSERT INTO users (user_id, guild_id, xp, level)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(user_id, guild_id) DO UPDATE SET xp = xp + ?
        """, (user_id, guild_id, amount, amount))
        await self.db.commit()
        
        async with self.db.execute("SELECT xp FROM users WHERE user_id = ? AND guild_id = ?", (user_id, guild_id)) as cursor:
            row = await cursor.fetchone()
            return row['xp'] if row else 0

    async def admin_set_level(self, user_id: int, guild_id: int, level: int):
        """Sets a user's level and resets XP to minimum for that level."""
        required_xp = self.get_total_xp_for_level(level)
            
        await self.db.execute("""
            INSERT INTO users (user_id, guild_id, xp, level)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, guild_id) DO UPDATE SET xp = ?, level = ?
        """, (user_id, guild_id, required_xp, level, required_xp, level))
        await self.db.commit()
        return required_xp

    async def admin_sync_xp(self, channel, limit: int = 1000) -> int:
        """Scans channel history and backfills XP. Returns count of users updated."""
        user_counts = {}
        async for message in channel.history(limit=limit):
            if message.author.bot: continue
            uid = message.author.id
            user_counts[uid] = user_counts.get(uid, 0) + 1
            
        if not user_counts: return 0

        for user_id, count in user_counts.items():
            xp_to_add = count * 10
            await self.db.execute("""
                INSERT INTO users (user_id, guild_id, xp, level)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(user_id, guild_id) DO UPDATE SET xp = xp + ?
            """, (user_id, channel.guild.id, xp_to_add, xp_to_add))
        await self.db.commit()
        return len(user_counts)

    async def admin_add_reward(self, guild_id: int, level: int, role_id: int):
        """Adds a level reward."""
        await self.db.execute("""
            INSERT INTO level_rewards (guild_id, level, role_id)
            VALUES (?, ?, ?)
            ON CONFLICT(guild_id, level) DO UPDATE SET role_id = ?
        """, (guild_id, level, role_id, role_id))
        await self.db.commit()

    async def admin_remove_reward(self, guild_id: int, level: int):
        """Removes a level reward."""
        await self.db.execute("DELETE FROM level_rewards WHERE guild_id = ? AND level = ?", (guild_id, level))
        await self.db.commit()

    async def get_rewards_config(self, guild_id: int):
        """Returns list of dicts {level, role_id}."""
        async with self.db.execute("SELECT level, role_id FROM level_rewards WHERE guild_id = ? ORDER BY level ASC", (guild_id,)) as cursor:
            rows = await cursor.fetchall()
            return [{"level": r['level'], "role_id": r['role_id']} for r in rows]


    async def cog_load(self):
        """
        Called when the Cog is loaded. We set up the database here.
        This is an Async operation, which is why we use aiosqlite.
        """
        # Connect to the SQLite database
        # This creates the file if it doesn't exist.
        self.db = await aiosqlite.connect(DB_FILE)
        
        # Enable row factory to get results as accessible objects/dicts instead of just tuples
        self.db.row_factory = aiosqlite.Row

        # Create the table if it doesn't exist
        # CHECK: We use IF NOT EXISTS so this is safe to run every time.
        # columns:
        #   user_id: The Discord User ID (Primary Key - must be unique)
        #   guild_id: The Server ID (Composite key with user usually, but for simplicity we filter by it)
        #   xp: Total experience points
        #   level: Current level
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER,
                guild_id INTEGER,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                PRIMARY KEY (user_id, guild_id)
            )
        """)
        
        # Create table for level rewards
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS level_rewards (
                guild_id INTEGER,
                level INTEGER,
                role_id INTEGER,
                PRIMARY KEY (guild_id, level)
            )
        """)
        
        await self.db.commit()
        print("Levels Cog: Database connected and table verified.")

    async def cog_unload(self):
        """Close the database connection when the Cog is unloaded"""
        if self.db:
            await self.db.close()

    @commands.Cog.listener()
    async def on_message(self, message):
        """
        Listen to every message to award XP.
        """
        # 1. Ignore bots (including ourselves) to prevent infinite loops
        if message.author.bot:
            return
        
        # 2. Ignore DMs
        if not message.guild:
            return

        # --- Cooldown Check ---
        now = time.time()
        last_xp = self.cooldowns.get(message.author.id, 0)
        if now - last_xp < 10: # 10 seconds cooldown
            return
            
        self.cooldowns[message.author.id] = now
        # ----------------------

        # 3. Add XP
        # We award 10 XP per message for this prototype.
        xp_gain = 10
        
        # SQL: UPSERT (Insert or Update)
        # We try to Insert the user. If they exist (Conflict on Primary Key), we just Update their XP.
        cursor = await self.db.execute("""
            INSERT INTO users (user_id, guild_id, xp, level)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(user_id, guild_id) DO UPDATE SET xp = xp + ?
        """, (message.author.id, message.guild.id, xp_gain, xp_gain))
        
        # 4. Check for Level Up
        # Just for efficiency, we only fetch the new values to check level up
        await self.db.commit()
        
        async with self.db.execute("""
            SELECT xp, level FROM users WHERE user_id = ? AND guild_id = ?
        """, (message.author.id, message.guild.id)) as cursor:
            row = await cursor.fetchone()
            if row:
                current_xp = row['xp']
                current_level = row['level']
                
                # Formula: Quadratic Scaling
                next_level_xp = self.get_xp_for_next_level(current_level)
                
                if current_xp >= next_level_xp:
                    new_level = current_level + 1
                    await self.db.execute("""
                        UPDATE users SET level = ? WHERE user_id = ? AND guild_id = ?
                    """, (new_level, message.author.id, message.guild.id))
                    await self.db.commit()
                    
                    # Notify the user
                    await message.channel.send(f"🎉 {message.author.mention} has leveled up to **Level {new_level}**!")

                    # Check for Role Rewards
                    async with self.db.execute("SELECT role_id FROM level_rewards WHERE guild_id = ? AND level = ?", (message.guild.id, new_level)) as cursor:
                        reward_row = await cursor.fetchone()
                        if reward_row:
                            role_id = reward_row['role_id']
                            role = message.guild.get_role(role_id)
                            if role:
                                try:
                                    await message.author.add_roles(role)
                                    await message.channel.send(f"🎁 You've been awarded the **{role.name}** role!")
                                except discord.Forbidden:
                                    await message.channel.send("⚠️ I tried to give you a reward role, but I don't have permission! Please check my role hierarchy.")
                                except discord.HTTPException:
                                    pass # Ignore other errors for now

    # --- Commands ---

    @app_commands.command(name="rank", description="Check your current rank and XP")
    async def rank(self, interaction: discord.Interaction, member: discord.Member = None):
        """
        Fetch data from SQLite and display it.
        """
        target = member or interaction.user
        
        async with self.db.execute("""
            SELECT xp, level FROM users WHERE user_id = ? AND guild_id = ?
        """, (target.id, interaction.guild.id)) as cursor:
            row = await cursor.fetchone()
            
        if row:
            xp = row['xp']
            level = row['level']
            
            # Show progress to next level
            next_xp_req = self.get_xp_for_next_level(level)
            
            embed = discord.Embed(title=f"Rank: {target.display_name}", color=discord.Color.blue())
            embed.add_field(name="Level", value=str(level), inline=True)
            embed.add_field(name="Total XP", value=f"{xp} / {next_xp_req} (Next Level)", inline=True)
            embed.set_thumbnail(url=target.avatar.url if target.avatar else None)
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(f"❌ {target.display_name} hasn't sent any messages yet!", ephemeral=True)

    @app_commands.command(name="leaderboard", description="Show the top 10 chatters")
    async def leaderboard(self, interaction: discord.Interaction):
        """
        SQL makes sorting easy using 'ORDER BY'.
        """
        async with self.db.execute("""
            SELECT user_id, xp, level FROM users 
            WHERE guild_id = ? 
            ORDER BY xp DESC 
            LIMIT 10
        """, (interaction.guild.id,)) as cursor:
            rows = await cursor.fetchall()
            
        if not rows:
            await interaction.response.send_message("No data yet!", ephemeral=True)
            return

        embed = discord.Embed(title="🏆 Server Leaderboard", color=discord.Color.gold())
        description = ""
        
        for index, row in enumerate(rows, start=1):
            user_id = row['user_id']
            # We try to fetch member from cache mainly
            member = interaction.guild.get_member(user_id)
            name = member.display_name if member else f"User {user_id}"
            
            description += f"**{index}. {name}** - Lvl {row['level']} ({row['xp']} XP)\n"
            
        embed.description = description
        await interaction.response.send_message(embed=embed)
    
    # --- DEPRECATED: Replaced by Admin Panel ---
    
    # @app_commands.command(name="sync_xp", description="[Admin] Scan chat history to backfill XP")
    # @app_commands.checks.has_permissions(administrator=True)
    # async def sync_xp(self, interaction: discord.Interaction, limit: int = 1000):
    #     """
    #     This is a 'Migration' script essentially.
    #     It scans the current channel history and awards XP retroactively.
    #     """
    #     await interaction.response.send_message(f"🔄 Starting sync... Scanning last {limit} messages. This might take a moment.", ephemeral=True)
    #     
    #     # 1. Count messages per user in memory first (to reduce DB writes)
    #     user_counts = {}
    #     
    #     # interaction.channel is where the command was run
    #     async for message in interaction.channel.history(limit=limit):
    #         if message.author.bot:
    #             continue
    #         
    #         uid = message.author.id
    #         user_counts[uid] = user_counts.get(uid, 0) + 1
    #         
    #     if not user_counts:
    #         await interaction.followup.send("No valid user messages found in the recent history.")
    #         return
    # 
    #     # 2. Bulk Update Database
    #     count_updated = 0
    #     
    #     # We process each user found
    #     for user_id, count in user_counts.items():
    #         xp_to_add = count * 10
    #         
    #         # Same UPSERT logic
    #         await self.db.execute("""
    #             INSERT INTO users (user_id, guild_id, xp, level)
    #             VALUES (?, ?, ?, 1)
    #             ON CONFLICT(user_id, guild_id) DO UPDATE SET xp = xp + ?
    #         """, (user_id, interaction.guild.id, xp_to_add, xp_to_add))
    #         
    #         count_updated += 1
    # 
    #     # 3. Recalculate Levels for everyone (Bulk Fix)
    #     # Simple formula update: Set level based on total XP
    #     # E.g. Level = floor(xp / 100) + 1 roughly, but for our logic:
    #     # We iterate and check manually or use a math formula if SQL supports it well.
    #     # For prototype, let's just commit the XP. Level up will happen on next message 
    #     # OR we can run a quick check now.
    #     
    #     # Let's simple commit for now
    #     await self.db.commit()
    # 
    #     await interaction.followup.send(f"✅ Sync Complete! Updated XP for {count_updated} users based on {limit} messages.\nUsers might level up on their next message!")
    
    # --- Level Management Commands ---
    
    # level_group = app_commands.Group(name="level", description="Manage level rewards")
    # 
    # @level_group.command(name="set_reward", description="Set a role reward for a level")
    # @app_commands.checks.has_permissions(manage_roles=True)
    # async def set_reward(self, interaction: discord.Interaction, level: int, role: discord.Role):
    #     """
    #     Configure a role to be given when a user reaches a specific level.
    #     """
    #     if role.position >= interaction.guild.me.top_role.position:
    #         await interaction.response.send_message(f"❌ I cannot assign the role {role.mention} because it is higher than or equal to my highest role.", ephemeral=True)
    #         return
    # 
    #     await self.db.execute("""
    #         INSERT INTO level_rewards (guild_id, level, role_id)
    #         VALUES (?, ?, ?)
    #         ON CONFLICT(guild_id, level) DO UPDATE SET role_id = ?
    #     """, (interaction.guild.id, level, role.id, role.id))
    #     await self.db.commit()
    #     
    #     await interaction.response.send_message(f"✅ Level {level} reward set to {role.mention}!", ephemeral=True)
    # 
    # @level_group.command(name="remove_reward", description="Remove a reward for a level")
    # @app_commands.checks.has_permissions(manage_roles=True)
    # async def remove_reward(self, interaction: discord.Interaction, level: int):
    #     """
    #     Remove a configured role reward for a specific level.
    #     """
    #     await self.db.execute("DELETE FROM level_rewards WHERE guild_id = ? AND level = ?", (interaction.guild.id, level))
    #     await self.db.commit()
    #     
    #     await interaction.response.send_message(f"✅ Removed reward for Level {level}.", ephemeral=True)
    # 
    # @level_group.command(name="rewards", description="List all level rewards")
    # async def list_rewards(self, interaction: discord.Interaction):
    #     """
    #     List all configured rewards for this server.
    #     """
    #     async with self.db.execute("SELECT level, role_id FROM level_rewards WHERE guild_id = ? ORDER BY level ASC", (interaction.guild.id,)) as cursor:
    #         rows = await cursor.fetchall()
    #         
    #     if not rows:
    #         await interaction.response.send_message("No level rewards configured yet.", ephemeral=True)
    #         return
    # 
    #     embed = discord.Embed(title="🎁 Level Rewards", color=discord.Color.purple())
    #     description = ""
    #     for row in rows:
    #         role = interaction.guild.get_role(row['role_id'])
    #         role_name = role.mention if role else f"Deleted Role ({row['role_id']})"
    #         description += f"**Level {row['level']}**: {role_name}\n"
    #         
    #     embed.description = description
    #     await interaction.response.send_message(embed=embed)
    # 
    # @level_group.command(name="give_xp", description="Give (or take) XP from a user")
    # @app_commands.checks.has_permissions(administrator=True)
    # async def give_xp(self, interaction: discord.Interaction, member: discord.Member, amount: int):
    #     """
    #     Manually add or remove XP from a user. 
    #     Note: This does NOT automatically check for level up/down recursively perfectly, 
    #     but we will run a quick check.
    #     """
    #     if member.bot:
    #         await interaction.response.send_message("🤖 Bots don't need XP!", ephemeral=True)
    #         return
    # 
    #     # Simple UPSERT to ensure user exists
    #     await self.db.execute("""
    #         INSERT INTO users (user_id, guild_id, xp, level)
    #         VALUES (?, ?, ?, 1)
    #         ON CONFLICT(user_id, guild_id) DO UPDATE SET xp = xp + ?
    #     """, (member.id, interaction.guild.id, amount, amount))
    #     
    #     await self.db.commit()
    #     
    #     # Now check their new status
    #     async with self.db.execute("SELECT xp, level FROM users WHERE user_id = ? AND guild_id = ?", (member.id, interaction.guild.id)) as cursor:
    #         row = await cursor.fetchone()
    #         new_xp = row['xp']
    #         current_level = row['level']
    #         
    #     # Very basic check: If XP is enough for next level, or too low for current.
    #     # For a full system, we might want a 'recalculate_level' helper function.
    #     # For now, let's just confirm the action.
    #     await interaction.response.send_message(f"✅ Adjusted {member.mention}'s XP by {amount}. New Total: {new_xp}", ephemeral=True)
    # 
    # @level_group.command(name="set_level", description="Set a user's level directly")
    # @app_commands.checks.has_permissions(administrator=True)
    # async def set_level(self, interaction: discord.Interaction, member: discord.Member, level: int):
    #     """
    #     Force set a user's level. This will reset their XP to the minimum required for that level.
    #     """
    #     if level < 1:
    #         await interaction.response.send_message("❌ Level must be at least 1.", ephemeral=True)
    #         return
    #         
    #     # Calculate minimum XP for this level
    #     # Based on our formula: Level 1=0-99, Level 2=100+, Level 3=300+ (Wait, our formula was recursive/iterative in on_message)
    #     # on_message logic: "next_level_xp = current_level * 100".
    #     # This implies a triangular number series: 
    #     # Lvl 1->2: 100xp (Total 100)
    #     # Lvl 2->3: 200xp (Total 300)
    #     # Lvl 3->4: 300xp (Total 600)
    #     # Formula for Total XP for Level L = 100 * (L * (L-1) / 2) roughly?
    #     # Let's double check logic:
    #     # if current_xp >= current_level * 100: level up.
    #     # This means to BE at Level 2, you needed 100 XP.
    #     # To BE at Level 3, you needed 100 (for L1) + 200 (for L2) = 300 XP.
    #     # Sum of 100*i for i=1 to L-1
    #     
    #     required_xp = 0
    #     for i in range(1, level):
    #         required_xp += i * 100
    #         
    #     await self.db.execute("""
    #         INSERT INTO users (user_id, guild_id, xp, level)
    #         VALUES (?, ?, ?, ?)
    #         ON CONFLICT(user_id, guild_id) DO UPDATE SET xp = ?, level = ?
    #     """, (member.id, interaction.guild.id, required_xp, level, required_xp, level))
    #     await self.db.commit()
    #     
    #     await interaction.response.send_message(f"✅ Set {member.mention} to **Level {level}** (XP set to {required_xp}).", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Levels(bot))

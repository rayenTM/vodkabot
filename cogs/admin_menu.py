import discord
from discord.ext import commands
from discord import app_commands
import os

# --- MODALS ---

class GiveXPModal(discord.ui.Modal, title="Give XP to User"):
    user_id = discord.ui.TextInput(label="User ID", placeholder="18-digit ID", required=True, min_length=15, max_length=20)
    amount = discord.ui.TextInput(label="Amount", placeholder="Integer (e.g. 100 or -50)", required=True, max_length=10)

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        try:
            uid = int(self.user_id.value)
            amt = int(self.amount.value)
        except ValueError:
            await interaction.response.send_message("❌ Invalid Input: ID and Amount must be integers.", ephemeral=True)
            return

        levels_cog = self.bot.get_cog("Levels")
        if not levels_cog:
            await interaction.response.send_message("❌ Levels system not loaded.", ephemeral=True)
            return

        new_xp = await levels_cog.admin_give_xp(uid, interaction.guild.id, amt)
        await interaction.response.send_message(f"✅ Adjusted XP for <@{uid}> by {amt}. New Total: {new_xp}", ephemeral=True)

class SetLevelModal(discord.ui.Modal, title="Set User Level"):
    user_id = discord.ui.TextInput(label="User ID", placeholder="18-digit ID", required=True, min_length=15, max_length=20)
    level_val = discord.ui.TextInput(label="New Level", placeholder="Target level (1+)", required=True, max_length=5)

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        try:
            uid = int(self.user_id.value)
            lvl = int(self.level_val.value)
        except ValueError:
            await interaction.response.send_message("❌ Invalid Input: Integers only.", ephemeral=True)
            return

        if lvl < 1:
            await interaction.response.send_message("❌ Level must be at least 1.", ephemeral=True)
            return

        levels_cog = self.bot.get_cog("Levels")
        if not levels_cog:
            await interaction.response.send_message("❌ Levels system not loaded.", ephemeral=True)
            return

        required_xp = await levels_cog.admin_set_level(uid, interaction.guild.id, lvl)
        await interaction.response.send_message(f"✅ Set <@{uid}> to **Level {lvl}** (XP reset to {required_xp}).", ephemeral=True)

class AddPropConfModal(discord.ui.Modal, title="Add Level Reward"):
    level = discord.ui.TextInput(label="Level", placeholder="e.g. 10", required=True, max_length=5)
    role_id = discord.ui.TextInput(label="Role ID", placeholder="18-digit Role ID", required=True, min_length=15, max_length=20)

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        try:
            lvl = int(self.level.value)
            rid = int(self.role_id.value)
        except ValueError:
            await interaction.response.send_message("❌ Integers only", ephemeral=True)
            return

        levels_cog = self.bot.get_cog("Levels")
        if not levels_cog: return

        await levels_cog.admin_add_reward(interaction.guild.id, lvl, rid)
        await interaction.response.send_message(f"✅ Reward set: Level {lvl} -> <@&{rid}>", ephemeral=True)

class RemoveRewardModal(discord.ui.Modal, title="Remove Level Reward"):
    level = discord.ui.TextInput(label="Level", placeholder="e.g. 10", required=True, max_length=5)

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        try:
            lvl = int(self.level.value)
        except ValueError:
            return

        levels_cog = self.bot.get_cog("Levels")
        if not levels_cog: return

        await levels_cog.admin_remove_reward(interaction.guild.id, lvl)
        await interaction.response.send_message(f"✅ Removed reward for Level {lvl}", ephemeral=True)

class CreateCategoryModal(discord.ui.Modal, title="Create Role Category"):
    name = discord.ui.TextInput(label="Category Name", placeholder="e.g. Pronouns", required=True)
    description = discord.ui.TextInput(label="Description", placeholder="User facing description", required=False)
    exclusive = discord.ui.TextInput(label="Exclusive? (y/n)", placeholder="y for Radio, n for Checkbox", required=True, max_length=3)
    
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        roles_cog = self.bot.get_cog("Roles")
        if not roles_cog: return
        
        is_excl = self.exclusive.value.lower().startswith('y')
        success = roles_cog.admin_create_category(self.name.value, self.description.value, is_excl)
        
        if success:
             await interaction.response.send_message(f"✅ Created category **{self.name.value}**.", ephemeral=True)
        else:
             await interaction.response.send_message(f"❌ **{self.name.value}** already exists!", ephemeral=True)

class AddRoleToCategoryModal(discord.ui.Modal, title="Add Role to Category"):
    cat_name = discord.ui.TextInput(label="Category Name", placeholder="Exact name", required=True)
    role_id = discord.ui.TextInput(label="Role ID", required=True)
    label = discord.ui.TextInput(label="Label", placeholder="Display Name", required=True)
    emoji = discord.ui.TextInput(label="Emoji", placeholder="e.g. 🔴", required=False)

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        roles_cog = self.bot.get_cog("Roles")
        if not roles_cog: return

        try:
             rid = int(self.role_id.value)
        except ValueError:
             await interaction.response.send_message("❌ Invalid Role ID.", ephemeral=True)
             return

        result = roles_cog.admin_add_role(self.cat_name.value, rid, self.label.value, self.emoji.value)
        
        if result == 'OK':
             await interaction.response.send_message(f"✅ Added **{self.label.value}** to **{self.cat_name.value}**.", ephemeral=True)
        elif result == 'CAT_NOT_FOUND':
             await interaction.response.send_message("❌ Category not found.", ephemeral=True)
        elif result == 'ROLE_EXISTS':
             await interaction.response.send_message("❌ Role already in category.", ephemeral=True)


class RemoveRoleFromCategoryModal(discord.ui.Modal, title="Remove Role from Category"):
    cat_name = discord.ui.TextInput(label="Category Name", required=True)
    identifier = discord.ui.TextInput(label="Role ID or Label", required=True)
    
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        roles_cog = self.bot.get_cog("Roles")
        if not roles_cog: return

        result = roles_cog.admin_remove_role(self.cat_name.value, self.identifier.value)
        
        if result == 'OK':
             await interaction.response.send_message(f"✅ Removed role from **{self.cat_name.value}**.", ephemeral=True)
        elif result == 'CAT_NOT_FOUND':
             await interaction.response.send_message("❌ Category not found.", ephemeral=True)
        elif result == 'ROLE_NOT_FOUND':
             await interaction.response.send_message("❌ Role not found in category.", ephemeral=True)

class DeleteCategoryModal(discord.ui.Modal, title="Delete Category"):
    name = discord.ui.TextInput(label="Category Name to Delete", required=True)
    confirm = discord.ui.TextInput(label="Type DELETE to confirm", required=True)
    
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        if self.confirm.value != "DELETE":
            await interaction.response.send_message("❌ Confirmation failed.", ephemeral=True)
            return

        roles_cog = self.bot.get_cog("Roles")
        if not roles_cog: return
        
        success = roles_cog.admin_delete_category(self.name.value)
        if success:
            await interaction.response.send_message(f"✅ Deleted category **{self.name.value}**.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Category not found.", ephemeral=True)


# --- VIEWS ---

class RewardsManageView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=180)
        self.bot = bot

    @discord.ui.button(label="List Rewards", style=discord.ButtonStyle.secondary, emoji="📜")
    async def list_rewards(self, interaction: discord.Interaction, button: discord.ui.Button):
        levels_cog = self.bot.get_cog("Levels")
        if not levels_cog: return 
        
        current_rewards = await levels_cog.get_rewards_config(interaction.guild.id)
            
        desc = ""
        for row in current_rewards:
            desc += f"**Lvl {row['level']}**: <@&{row['role_id']}>\n"
        
        embed = discord.Embed(title="Current Level Rewards", description=desc or "No rewards configured.", color=discord.Color.blue())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Add Reward", style=discord.ButtonStyle.success, emoji="➕")
    async def add_reward(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AddPropConfModal(self.bot))

    @discord.ui.button(label="Remove Reward", style=discord.ButtonStyle.danger, emoji="➖")
    async def remove_reward(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RemoveRewardModal(self.bot))

class RolesManageView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=180)
        self.bot = bot

    @discord.ui.button(label="Create Category", style=discord.ButtonStyle.success, emoji="📁", row=0)
    async def create_cat(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CreateCategoryModal(self.bot))

    @discord.ui.button(label="Delete Category", style=discord.ButtonStyle.danger, emoji="🗑️", row=0)
    async def del_cat(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(DeleteCategoryModal(self.bot))

    @discord.ui.button(label="Add Role", style=discord.ButtonStyle.success, emoji="➕", row=1)
    async def add_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AddRoleToCategoryModal(self.bot))

    @discord.ui.button(label="Remove Role", style=discord.ButtonStyle.danger, emoji="➖", row=1)
    async def rm_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RemoveRoleFromCategoryModal(self.bot))


class AdminControlView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    # --- ROW 0: Quick Actions ---
    @discord.ui.button(label="Check Ping", style=discord.ButtonStyle.secondary, emoji="🏓", row=0)
    async def check_ping(self, interaction: discord.Interaction, button: discord.ui.Button):
        latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"🏓 Pong! **{latency}ms**", ephemeral=True)

    @discord.ui.button(label="Sync XP (All)", style=discord.ButtonStyle.danger, emoji="🔄", row=0)
    async def sync_xp_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        levels_cog = self.bot.get_cog("Levels")
        if not levels_cog:
            await interaction.response.send_message("❌ Levels system not loaded.", ephemeral=True)
            return

        # Defer because history scanning takes time
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send("⏳ Starting sync... Scanning last 1000 messages...")

        count_updated = await levels_cog.admin_sync_xp(interaction.channel, 1000)
        await interaction.followup.send(f"✅ Sync Complete! Updated XP for {count_updated} users.")

    @discord.ui.button(label="Spawn Role Button", style=discord.ButtonStyle.primary, emoji="🎭", row=0)
    async def spawn_role_menu(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            from cogs.roles import MasterView
            embed = discord.Embed(
                title="Self-Assignable Roles",
                description="Click the button below to browse and assign roles to yourself!",
                color=discord.Color.gold()
            )
            await interaction.channel.send(embed=embed, view=MasterView())
            await interaction.response.send_message("✅ Spawned.", ephemeral=True)
        except:
             await interaction.response.send_message("❌ Error spawning view.", ephemeral=True)

    # --- ROW 1: User Management ---
    @discord.ui.button(label="Give XP", style=discord.ButtonStyle.secondary, emoji="✨", row=1)
    async def give_xp_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(GiveXPModal(self.bot))

    @discord.ui.button(label="Set Level", style=discord.ButtonStyle.secondary, emoji="📶", row=1)
    async def set_level_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SetLevelModal(self.bot))

    # --- ROW 2: Configuration ---
    @discord.ui.button(label="Manage Rewards", style=discord.ButtonStyle.primary, emoji="🎁", row=2)
    async def manage_rewards(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Select an action:", view=RewardsManageView(self.bot), ephemeral=True)

    @discord.ui.button(label="Manage Roles", style=discord.ButtonStyle.primary, emoji="🛠️", row=2)
    async def manage_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Select an action:", view=RolesManageView(self.bot), ephemeral=True)


class AdminMenu(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="controlpanel", description="[Admin] Open the Secret Control Menu")
    @app_commands.checks.has_permissions(administrator=True)
    async def control_panel(self, interaction: discord.Interaction):
        """
        Opens the secret admin menu.
        """
        # Gather Stats for Dashboard
        # Latency
        ping = round(self.bot.latency * 1000)
        
        # Stats from Cogs
        role_stats = "N/A"
        reward_stats = "N/A"
        
        roles_cog = self.bot.get_cog("Roles")
        if roles_cog:
            conf = roles_cog.get_role_config()
            role_stats = len(conf.get('categories', []))

        levels_cog = self.bot.get_cog("Levels")
        if levels_cog:
             rewards = await levels_cog.get_rewards_config(interaction.guild.id)
             reward_stats = len(rewards)

        embed = discord.Embed(
            title="🎛️ Admin Control Panel", 
            description="Centralized Management Dashboard",
            color=discord.Color.dark_theme()
        )
        
        embed.add_field(name="⚙️ System", value=f"Ping: `{ping}ms`\nStatus: `Online`", inline=True)
        embed.add_field(name="📊 Statistics", value=f"Reward Tiers: `{reward_stats}`\nRole Categories: `{role_stats}`", inline=True)
        
        embed.set_footer(text="Select an action below to manage the bot.")
        
        await interaction.response.send_message(embed=embed, view=AdminControlView(self.bot), ephemeral=True)

async def setup(bot):
    await bot.add_cog(AdminMenu(bot))

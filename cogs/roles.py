import discord
from discord.ext import commands
from discord import app_commands
import json
import os

# Path to the JSON file
ROLES_FILE = "/app/data/roles.json" if os.path.exists("/app/data") else "./data/roles.json"

def load_roles_config():
    if not os.path.exists(ROLES_FILE):
        return {"colors": [], "hobbies": []}
    try:
        with open(ROLES_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {"colors": [], "hobbies": []}

def save_roles_config(data):
    # Ensure directory exists
    os.makedirs(os.path.dirname(ROLES_FILE), exist_ok=True)
    with open(ROLES_FILE, "w") as f:
        json.dump(data, f, indent=4)

class ColorSelect(discord.ui.Select):
    def __init__(self, options_data):
        options = []
        for item in options_data:
            # item: {'id': 123, 'label': 'Red', 'emoji': '🔴'}
            options.append(discord.SelectOption(
                label=item['label'],
                value=str(item['id']), # Value must be string
                emoji=item.get('emoji'),
                description=f"Get the {item['label']} role"
            ))
        
        if not options:
            options.append(discord.SelectOption(label="No roles configured", value="none", description="Ask admin to config"))

        super().__init__(
            placeholder="Choose your color...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="role_menu:colors"
        )

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message("No roles are currently configured.", ephemeral=True)
            return

        selected_role_id = int(self.values[0])
        selected_role = interaction.guild.get_role(selected_role_id)
        
        if not selected_role:
             await interaction.response.send_message(f"Role with ID **{selected_role_id}** not found! It might have been deleted.", ephemeral=True)
             return

        # 1. Remove OTHER color roles (Mutual Exclusivity)
        # We need to check against ALL color roles defined in the current config
        role_config = load_roles_config()
        color_role_ids = [item['id'] for item in role_config.get('colors', [])]
        
        roles_to_remove = []
        for r_id in color_role_ids:
            if r_id != selected_role_id:
                r = interaction.guild.get_role(r_id)
                if r and r in interaction.user.roles:
                    roles_to_remove.append(r)
        
        if roles_to_remove:
            try:
                await interaction.user.remove_roles(*roles_to_remove)
            except discord.Forbidden:
                await interaction.response.send_message("❌ Error: I don't have permission to remove old roles. Check hierarchy.", ephemeral=True)
                return

        # 2. Toggle the selected role
        try:
            if selected_role in interaction.user.roles:
                await interaction.user.remove_roles(selected_role)
                await interaction.response.send_message(f"Removed **{selected_role.name}**.", ephemeral=True)
            else:
                await interaction.user.add_roles(selected_role)
                msg = f"You are now **{selected_role.name}**!"
                if roles_to_remove:
                    msg += " (Removed other colors)"
                await interaction.response.send_message(msg, ephemeral=True)
        except discord.Forbidden:
             await interaction.response.send_message(f"❌ Error: I cannot assign **{selected_role.name}**. My role must be higher than it!", ephemeral=True)


class HobbySelect(discord.ui.Select):
    def __init__(self, options_data):
        options = []
        for item in options_data:
            options.append(discord.SelectOption(
                label=item['label'],
                value=str(item['id']),
                emoji=item.get('emoji'),
                description=f"Toggle {item['label']} role"
            ))

        if not options:
            options.append(discord.SelectOption(label="No hobbies configured", value="none"))

        # max_values=len(options) lets them pick all of them
        super().__init__(
            placeholder="Select to toggle hobbies...",
            min_values=1,
            max_values=max(1, len(options)), # Ensure max_values is at least 1
            options=options,
            custom_id="role_menu:hobbies"
        )

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message("No hobbies configured.", ephemeral=True)
            return

        response_parts = []
        
        for role_id_str in self.values:
            role_id = int(role_id_str)
            role = interaction.guild.get_role(role_id)
            
            if role:
                if role in interaction.user.roles:
                    try:
                        await interaction.user.remove_roles(role)
                        response_parts.append(f"Removed **{role.name}**")
                    except discord.Forbidden:
                        response_parts.append(f"❌ Failed to remove **{role.name}**")
                else:
                    try:
                        await interaction.user.add_roles(role)
                        response_parts.append(f"Added **{role.name}**")
                    except discord.Forbidden:
                        response_parts.append(f"❌ Failed to add **{role.name}**")
            else:
                response_parts.append(f"❌ Role ID **{role_id}** not found")

        await interaction.response.send_message(", ".join(response_parts), ephemeral=True)


class RoleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
        # Load fresh config
        config = load_roles_config()
        
        # Only add dropdowns if there are options, or placeholders
        self.add_item(ColorSelect(config.get('colors', [])))
        self.add_item(HobbySelect(config.get('hobbies', [])))


class Roles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # We register a View so the bot listens to the custom_ids.
        # Even if the config changes later, as long as custom_ids are stable,
        # the bot will receive the interaction. 
        # Note: The View registered here uses the config AT STARTUP time.
        # But since we create a NEW View every time we send the menu, 
        # and the interactions are handled by constructing a View state,
        # we generally rely on the fact that persistence works via custom_id.
        self.bot.add_view(RoleView())
        print("RoleView registered for persistence.")

    @app_commands.command(name="rolemenu", description="Spawns the role selection menu (Admin only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def rolemenu(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Server Roles",
            description="Use the dropdowns below to select your roles!",
            color=discord.Color.gold()
        )
        embed.set_footer(text="Roles are updated simply by selecting them.")
        
        # Determine the updated View based on current JSON
        view = RoleView()
        await interaction.response.send_message(embed=embed, view=view)

    # --- Configuration Commands ---

    role_group = app_commands.Group(name="role_config", description="Manage dynamic roles")

    @role_group.command(name="add_color", description="Add a role to the Color dropdown (Mutually Exclusive)")
    @app_commands.describe(role="The role to add", label="Name in the menu", emoji="Emoji (optional)")
    @app_commands.checks.has_permissions(administrator=True)
    async def add_color(self, interaction: discord.Interaction, role: discord.Role, label: str, emoji: str = None):
        config = load_roles_config()
        
        new_entry = {
            "id": role.id,
            "label": label,
            "emoji": emoji or "🎨"
        }
        
        # Check against duplicates
        if any(c['id'] == role.id for c in config.get('colors', [])):
             await interaction.response.send_message(f"Role **{role.name}** is already in Colors!", ephemeral=True)
             return

        config.setdefault('colors', []).append(new_entry)
        save_roles_config(config)
        
        await interaction.response.send_message(f"✅ Added **{label}** ({role.name}) to Colors. Run `/rolemenu` to see changes.", ephemeral=True)

    @role_group.command(name="add_hobby", description="Add a role to the Hobby dropdown (Multi-select)")
    @app_commands.describe(role="The role to add", label="Name in the menu", emoji="Emoji (optional)")
    @app_commands.checks.has_permissions(administrator=True)
    async def add_hobby(self, interaction: discord.Interaction, role: discord.Role, label: str, emoji: str = None):
        config = load_roles_config()
        
        new_entry = {
            "id": role.id,
            "label": label,
            "emoji": emoji or "🎮"
        }
        
        if any(h['id'] == role.id for h in config.get('hobbies', [])):
             await interaction.response.send_message(f"Role **{role.name}** is already in Hobbies!", ephemeral=True)
             return

        config.setdefault('hobbies', []).append(new_entry)
        save_roles_config(config)
        
        await interaction.response.send_message(f"✅ Added **{label}** ({role.name}) to Hobbies. Run `/rolemenu` to see changes.", ephemeral=True)

    @role_group.command(name="remove", description="Remove a role from configuration by ID or Label")
    @app_commands.describe(category="colors or hobbies", identifier="Role Name (Label) or Role ID")
    @app_commands.choices(category=[
        app_commands.Choice(name="Colors", value="colors"),
        app_commands.Choice(name="Hobbies", value="hobbies")
    ])
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_role(self, interaction: discord.Interaction, category: str, identifier: str):
        config = load_roles_config()
        cat_list = config.get(category, [])
        
        # Filter out the item
        # We try to match by ID (int) or Label (str)
        initial_len = len(cat_list)
        
        new_list = []
        for item in cat_list:
            # Check if identifier matches id or label
            is_match = False
            if str(item['id']) == identifier:
                is_match = True
            elif item['label'].lower() == identifier.lower():
                is_match = True
            
            if not is_match:
                new_list.append(item)
        
        if len(new_list) == initial_len:
             await interaction.response.send_message(f"❌ Could not find a role matching **{identifier}** in {category}.", ephemeral=True)
             return

        config[category] = new_list
        save_roles_config(config)
        await interaction.response.send_message(f"✅ Removed matching role(s) from {category}. Run `/rolemenu` to update.", ephemeral=True)

    @role_group.command(name="list", description="List currently configured roles")
    async def list_roles(self, interaction: discord.Interaction):
        config = load_roles_config()
        
        embed = discord.Embed(title="Configured Roles", color=discord.Color.teal())
        
        colors = config.get('colors', [])
        if colors:
            desc = "\n".join([f"{c['emoji']} **{c['label']}** (ID: {c['id']})" for c in colors])
            embed.add_field(name="Colors (Exclusive)", value=desc, inline=False)
        else:
            embed.add_field(name="Colors", value="None configured", inline=False)
            
        hobbies = config.get('hobbies', [])
        if hobbies:
            desc = "\n".join([f"{h['emoji']} **{h['label']}** (ID: {h['id']})" for h in hobbies])
            embed.add_field(name="Hobbies (Multi)", value=desc, inline=False)
        else:
            embed.add_field(name="Hobbies", value="None configured", inline=False)
            
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Roles(bot))

import discord
from discord.ext import commands
from discord import app_commands
import json
import os

# Path to the JSON file
ROLES_FILE = "/app/data/roles.json" if os.path.exists("/app/data") else "./data/roles.json"

def load_roles_config():
    if not os.path.exists(ROLES_FILE):
        return {"categories": []}
    
    try:
        with open(ROLES_FILE, "r") as f:
             # We assume migration was handled or file is fresh.
             # If you need the migration logic again, we can keep it, 
             # but it's likely already run or not needed if file is new.
             # Keeping it simple for the view logic.
             data = json.load(f)
             if "colors" in data or "hobbies" in data:
                  # Quick migration re-implementation to be safe
                  new_categories = []
                  if "colors" in data and data["colors"]:
                      new_categories.append({"name": "Colors", "is_exclusive": True, "roles": data["colors"]})
                  if "hobbies" in data and data["hobbies"]:
                      new_categories.append({"name": "Hobbies", "is_exclusive": False, "roles": data["hobbies"]})
                  return {"categories": new_categories}
             return data
    except json.JSONDecodeError:
        return {"categories": []}

def save_roles_config(data):
    os.makedirs(os.path.dirname(ROLES_FILE), exist_ok=True)
    with open(ROLES_FILE, "w") as f:
        json.dump(data, f, indent=4)

class UserSpecificRoleSelect(discord.ui.Select):
    """
    A select menu tailored to a specific user's current roles.
    """
    def __init__(self, category, user, guild):
        self.category_name = category['name']
        self.is_exclusive = category.get('is_exclusive', False)
        self.roles_data = category.get('roles', [])
        self.guild = guild
        
        # Build options
        options = []
        user_role_ids = [r.id for r in user.roles]
        
        for item in self.roles_data:
            role_id = item['id']
            is_selected = role_id in user_role_ids
            
            options.append(discord.SelectOption(
                label=item['label'],
                value=str(role_id),
                emoji=item.get('emoji'),
                description=f"{'Selected' if is_selected else 'Select'} {item['label']}",
                default=is_selected 
            ))
        
        # Handle empty case
        if not options:
            options.append(discord.SelectOption(label="No roles configured", value="none"))

        # Determine Max Values
        # If exclusive: max 1.
        # If multi: max is len(options).
        max_vals = 1 if self.is_exclusive else len(options)
        max_vals = min(max(1, max_vals), 25)

        super().__init__(
            placeholder=f"Select {self.category_name}...",
            min_values=0 if not self.is_exclusive else 1, # Multi can deselect all. Exclusive usually implies 1, unless we allow 0? Let's say min 0 for multi.
            max_values=max_vals,
            options=options[:25]
        )

    async def callback(self, interaction: discord.Interaction):
        if self.values and self.values[0] == "none":
            await interaction.response.defer() # Do nothing
            return

        # Refetch user to get latest state? 
        # Actually interaction.user is cached. To be super safe we might want interaction.guild.get_member(user.id)
        # But for now, standard user object is okay.
        
        member = interaction.guild.get_member(interaction.user.id)
        if not member:
            return

        selected_ids = set(int(v) for v in self.values)
        
        # All potential role IDs in this category
        category_role_ids = set(r['id'] for r in self.roles_data)
        
        # Identify what to Add and what to Remove
        to_add = []
        to_remove = []

        if self.is_exclusive:
            # Exclusive Logic:
            # The user picked ONE value (or zero if we allowed min 0, but we set min 1 typically for radios. 
            # Actually standard generic Select min_values=1).
            # If they picked X, we must remove ALL other roles in this category.
            
            target_id = int(self.values[0])
            target_role =  interaction.guild.get_role(target_id)
            
            # Roles to remove: Any role in this category that the user HAS, except the chosen one
            for r_id in category_role_ids:
                if r_id != target_id:
                     role_obj = interaction.guild.get_role(r_id)
                     if role_obj and role_obj in member.roles:
                         to_remove.append(role_obj)
            
            # Role to add: The chosen one (if not already possessed)
            if target_role and target_role not in member.roles:
                to_add.append(target_role)

        else:
            # Multi-Select Logic (Sync State):
            # Iterate through ALL roles in this category.
            # If ID is in selected_ids -> Ensure user HAS it (Add if missing).
            # If ID is NOT in selected_ids -> Ensure user does NOT have it (Remove if present).
            
            for r_id in category_role_ids:
                role_obj = interaction.guild.get_role(r_id)
                if not role_obj: continue
                
                if r_id in selected_ids:
                    # User WANTS this role
                    if role_obj not in member.roles:
                        to_add.append(role_obj)
                else:
                    # User does NOT want this role (unchecked it)
                    if role_obj in member.roles:
                        to_remove.append(role_obj)

        # Apply Changes
        response_text = [] # Silent implementation? Or ephemeral feedback? 
        # Since the menu is ephemeral, feedback is good.
        
        try:
            if to_remove:
                await member.remove_roles(*to_remove)
                response_text.append(f"Removed: {', '.join(r.name for r in to_remove)}")
            
            if to_add:
                await member.add_roles(*to_add)
                response_text.append(f"Added: {', '.join(r.name for r in to_add)}")
                
        except discord.Forbidden:
            await interaction.response.send_message("❌ I do not have permission to manage these roles!", ephemeral=True)
            return
            
        final_msg = "Updated!" if not response_text else " | ".join(response_text)
        
        # We need to defer or edit to acknowledge the interaction so it doesn't fail
        # Re-sending the message updates the view state (checkboxes) automatically? 
        # No, we need to update the options to reflect new 'default' values if we want the menu to stay consistent.
        # But closing it is also fine.
        
        await interaction.response.send_message(final_msg, ephemeral=True)


class UserSpecificRoleView(discord.ui.View):
    def __init__(self, user, guild):
        super().__init__(timeout=180) # Ephemeral views can timeout
        
        config = load_roles_config()
        for cat in config.get('categories', []):
            self.add_item(UserSpecificRoleSelect(cat, user, guild))

class MasterRoleButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Open Role Menu",
            style=discord.ButtonStyle.primary,
            custom_id="role_menu:master_btn",
            emoji="🎭"
        )
        
    async def callback(self, interaction: discord.Interaction):
        view = UserSpecificRoleView(interaction.user, interaction.guild)
        if not view.children:
             await interaction.response.send_message("❌ No roles are currently configured.", ephemeral=True)
             return
        
        await interaction.response.send_message(
            "👇 **Select your roles below**\n"
            "• Use the dropdowns to pick your roles.\n"
            "• Checkboxes show what you currently have.", 
            view=view, 
            ephemeral=True
        )

class MasterView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(MasterRoleButton())

class Roles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- Public Admin Methods (API) ---
    
    def get_role_config(self):
        return load_roles_config()

    def admin_create_category(self, name: str, description: str, is_exclusive: bool) -> bool:
        """Returns True if created, False if already exists."""
        config = load_roles_config()
        if any(c['name'].lower() == name.lower() for c in config.get('categories', [])):
             return False
        config.setdefault('categories', []).append({
            "name": name, "description": description, "is_exclusive": is_exclusive, "roles": []
        })
        save_roles_config(config)
        return True

    def admin_delete_category(self, name: str) -> bool:
        """Returns True if deleted, False if not found."""
        config = load_roles_config()
        initial = len(config.get('categories', []))
        config['categories'] = [c for c in config.get('categories', []) if c['name'].lower() != name.lower()]
        if len(config.get('categories', [])) == initial:
            return False
        save_roles_config(config)
        return True

    def admin_add_role(self, category_name: str, role_id: int, label: str, emoji: str) -> str:
        """Returns 'OK', 'CAT_NOT_FOUND', or 'ROLE_EXISTS'."""
        config = load_roles_config()
        cat = next((c for c in config.get('categories', []) if c['name'].lower() == category_name.lower()), None)
        if not cat: return 'CAT_NOT_FOUND'
        
        if any(r['id'] == role_id for r in cat['roles']):
            return 'ROLE_EXISTS'
            
        cat['roles'].append({"id": role_id, "label": label, "emoji": emoji or "🔹"})
        save_roles_config(config)
        return 'OK'

    def admin_remove_role(self, category_name: str, identifier: str) -> str:
        """Returns 'OK', 'CAT_NOT_FOUND', or 'ROLE_NOT_FOUND'."""
        config = load_roles_config()
        cat = next((c for c in config.get('categories', []) if c['name'].lower() == category_name.lower()), None)
        if not cat: return 'CAT_NOT_FOUND'

        initial = len(cat['roles'])
        cat['roles'] = [r for r in cat['roles'] if str(r['id']) != identifier and r['label'].lower() != identifier.lower()]
        
        if len(cat['roles']) == initial:
             return 'ROLE_NOT_FOUND'
        
        save_roles_config(config)
        return 'OK'

    @commands.Cog.listener()
    async def on_ready(self):
        # Register the Master View (The one with the persistent button)
        self.bot.add_view(MasterView())
        print("Role MasterView registered.")

    # --- DEPRECATED: Replaced by Admin Panel ---
    
    # @app_commands.command(name="rolemenu", description="Spawns the 'Open Role Menu' button")
    # @app_commands.checks.has_permissions(administrator=True)
    # async def rolemenu(self, interaction: discord.Interaction):
    #     embed = discord.Embed(
    #         title="Self-Assignable Roles",
    #         description="Click the button below to browse and assign roles to yourself!",
    #         color=discord.Color.gold()
    #     )
    #     await interaction.response.send_message(embed=embed, view=MasterView())
    # 
    # # --- Configuration Commands ---
    # role_group = app_commands.Group(name="role_config", description="Manage dynamic role categories")
    # 
    # @role_group.command(name="create_category", description="Create a new role category")
    # @app_commands.describe(name="Name (e.g. Pronouns)", is_exclusive="True=Radio, False=Checkbox")
    # @app_commands.checks.has_permissions(administrator=True)
    # async def create_category(self, interaction: discord.Interaction, name: str, description: str, is_exclusive: bool):
    #     config = load_roles_config()
    #     if any(c['name'].lower() == name.lower() for c in config.get('categories', [])):
    #          await interaction.response.send_message(f"❌ **{name}** already exists!", ephemeral=True)
    #          return
    #     config.setdefault('categories', []).append({
    #         "name": name, "description": description, "is_exclusive": is_exclusive, "roles": []
    #     })
    #     save_roles_config(config)
    #     await interaction.response.send_message(f"✅ Created category **{name}**.", ephemeral=True)
    # 
    # @role_group.command(name="delete_category", description="Delete a category")
    # @app_commands.checks.has_permissions(administrator=True)
    # async def delete_category(self, interaction: discord.Interaction, name: str):
    #     config = load_roles_config()
    #     initial = len(config.get('categories', []))
    #     config['categories'] = [c for c in config.get('categories', []) if c['name'].lower() != name.lower()]
    #     if len(config['categories']) == initial:
    #         await interaction.response.send_message(f"❌ Category **{name}** not found.", ephemeral=True)
    #     else:
    #         save_roles_config(config)
    #         await interaction.response.send_message(f"✅ Deleted **{name}**.", ephemeral=True)
    # 
    # @role_group.command(name="add_role", description="Add a role to a category")
    # @app_commands.checks.has_permissions(administrator=True)
    # async def add_role(self, interaction: discord.Interaction, category_name: str, role: discord.Role, label: str, emoji: str = None):
    #     config = load_roles_config()
    #     cat = next((c for c in config.get('categories', []) if c['name'].lower() == category_name.lower()), None)
    #     if not cat:
    #         await interaction.response.send_message(f"❌ Category **{category_name}** not found.", ephemeral=True)
    #         return
    #     if any(r['id'] == role.id for r in cat['roles']):
    #         await interaction.response.send_message(f"❌ Role is already in this category!", ephemeral=True)
    #         return
    #     cat['roles'].append({"id": role.id, "label": label, "emoji": emoji or "🔹"})
    #     save_roles_config(config)
    #     await interaction.response.send_message(f"✅ Added **{label}** to **{category_name}**.", ephemeral=True)
    # 
    # @role_group.command(name="remove_role", description="Remove a role from a category")
    # @app_commands.checks.has_permissions(administrator=True)
    # async def remove_role(self, interaction: discord.Interaction, category_name: str, identifier: str):
    #     config = load_roles_config()
    #     cat = next((c for c in config.get('categories', []) if c['name'].lower() == category_name.lower()), None)
    #     if not cat:
    #         await interaction.response.send_message(f"❌ Category **{category_name}** not found.", ephemeral=True)
    #         return
    #     initial = len(cat['roles'])
    #     cat['roles'] = [r for r in cat['roles'] if str(r['id']) != identifier and r['label'].lower() != identifier.lower()]
    #     if len(cat['roles']) == initial:
    #          await interaction.response.send_message(f"❌ Role **{identifier}** not found.", ephemeral=True)
    #          return
    #     save_roles_config(config)
    #     await interaction.response.send_message(f"✅ Removed role from **{category_name}**.", ephemeral=True)
    # 
    # @role_group.command(name="list", description="List configurations")
    # async def list_config(self, interaction: discord.Interaction):
    #     config = load_roles_config()
    #     embed = discord.Embed(title="Dynamic Roles", color=discord.Color.blurple())
    #     for c in config.get('categories', []):
    #         roles = [f"{r.get('emoji','')} {r['label']}" for r in c['roles']]
    #         val = ", ".join(roles) if roles else "No roles"
    #         embed.add_field(name=f"{c['name']} ({'Radio' if c['is_exclusive'] else 'Checkbox'})", value=val, inline=False)
    #     await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Roles(bot))

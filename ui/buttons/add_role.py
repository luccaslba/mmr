import discord, emojis, asyncio, pytz, functions
from datetime import datetime, timezone, time
from discord import Embed
from discord.ui import View, Button, Modal, TextInput
from db import session, Users, Guild_Config, RolesMMR

class AddRoleModal(Modal, title="Adicionar Cargo"):
    role_id = TextInput(label="Id do cargo:", placeholder="12132", required=True)
    MMR_nes = TextInput(label="Quantidade de MMR necessario:", placeholder="8", required=True)

    def __init__(self):
        super().__init__(timeout=None)

    async def on_submit(self, interaction: discord.Interaction):
        guild = session.query(Guild_Config).filter_by(guild_id=interaction.guild.id).first()
        if guild:
            role_id = 0
            MMR_nes = 0
            try:
                role_id = int(self.role_id.value)
                MMR_nes = int(self.MMR_nes.value)
            except:
                failed = Embed(
                    title=f"{emojis.FAILED} | O id do cargo ou MMR necessario, precisa ser numero!",
                    color=discord.Color.red()
                )
                return await interaction.response.send_message(embed=failed, ephemeral=True)

            role_db = session.query(RolesMMR).filter_by(role_id=role_id).first()
            if not role_db:
                role = interaction.guild.get_role(role_id)
                if role:
                    add_role = RolesMMR(role.name, role_id, MMR_nes)
                    session.add(add_role)
                    session.commit()
                    sucess = Embed(
                        title=f"{emojis.SUCESS} | Cargo registrado com sucesso!",
                        color=discord.Color.green()
                    )
                    sucess.add_field(name="Cargo Adicionado:", value=role.name)
                    sucess.add_field(name="MMR Necessario:", value=MMR_nes, inline=False)

                    await interaction.response.send_message(embed=sucess, ephemeral=True)
                else:
                    failed = Embed(
                        title=f"{emojis.FAILED} | Cargo não existe!",
                        color=discord.Color.red()
                    )
                    await interaction.response.send_message(embed=failed, ephemeral=True)

            else:
                failed = Embed(
                    title=f"{emojis.FAILED} | Cargo já configurado!",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=failed, ephemeral=True)
        else:
            failed = Embed(
                title=f"{emojis.FAILED} | Servidor não está configurado!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=failed, ephemeral=True)

class EditRoleModal(Modal, title="Editar Cargo"):
    MMR_nes = TextInput(label="Quantidade de MMR que desejá modificar:", placeholder="8", required=True)

    def __init__(self, role):
        super().__init__(timeout=None)
        self.role = role

    async def on_submit(self, interaction: discord.Interaction):
        guild = session.query(Guild_Config).filter_by(guild_id=interaction.guild.id).first()
        if guild:
            MMR_nes = 0
            try:
                MMR_nes = int(self.MMR_nes.value)
            except:
                failed = Embed(
                    title=f"{emojis.FAILED} | O MMR, precisa ser numero!",
                    color=discord.Color.red()
                )
                return await interaction.response.send_message(embed=failed, ephemeral=True)

            antigo = self.role.MRR
            self.role.MRR = MMR_nes
            session.commit()
            sucess = Embed(
                title=f"{emojis.SUCESS} | Cargo editado com sucesso!",
                color=discord.Color.green()
            )
            sucess.add_field(name="MMR Antigo:", value=antigo)
            sucess.add_field(name="MMR Atual:", value=MMR_nes, inline=False)

            await interaction.response.send_message(embed=sucess, ephemeral=True)
        else:
            failed = Embed(
                title=f"{emojis.FAILED} | Servidor não está configurado!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=failed, ephemeral=True)

class RoleSelectDelete(discord.ui.Select):
    def __init__(self, roles):

        options = [
            discord.SelectOption(label=role.role_name, value=role.role_id)
            for role in roles
        ]
        super().__init__(
            placeholder="Selecione um cargo para deletar:",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        role_id = self.values[0]
        role = session.query(RolesMMR).filter_by(role_id=role_id).first()
        session.delete(role)
        session.commit()
        deleted = Embed(
            title=f"{emojis.LIXO} | Cargo deletado!",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=deleted, ephemeral=True)

class RoleSelectDeleteView(View):
    def __init__(self, roles):
        super().__init__(timeout=None)
        self.add_item(RoleSelectDelete(roles))

class RoleSelectEdit(discord.ui.Select):
    def __init__(self, roles):

        options = [
            discord.SelectOption(label=role.role_name, value=role.role_id)
            for role in roles
        ]
        super().__init__(
            placeholder="Selecione um cargo para deletar:",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        role_id = self.values[0]
        role = session.query(RolesMMR).filter_by(role_id=role_id).first()
        await interaction.response.send_modal(EditRoleModal(role))

class RoleSelectEditView(View):
    def __init__(self, roles):
        super().__init__(timeout=None)
        self.add_item(RoleSelectEdit(roles))

class RoleSelectDeleteView(View):
    def __init__(self, roles):
        super().__init__(timeout=None)
        self.add_item(RoleSelectDelete(roles))

class RoleSelectVer(discord.ui.Select):
    def __init__(self, roles):

        options = [
            discord.SelectOption(label=role.role_name, value=role.role_id)
            for role in roles
        ]
        super().__init__(
            placeholder="Selecione um cargo para deletar:",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        role_id = self.values[0]
        role = session.query(RolesMMR).filter_by(role_id=role_id).first()
        info = Embed(
            title=f"Informações:",
            color=discord.Color.green()
        )
        info.add_field(name="Cargo Nome:", value=role.role_name)
        info.add_field(name="Cargo ID:", value=role.role_id)
        info.add_field(name="MMR Necessario:", value=role.MRR)
        await interaction.response.send_message(embed=info, ephemeral=True)

class RoleSelectVerView(View):
    def __init__(self, roles):
        super().__init__(timeout=None)
        self.add_item(RoleSelectVer(roles))

class AddRoleView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Adicionar Cargo", style=discord.ButtonStyle.green, emoji=emojis.SUCESS, custom_id="add_role")
    async def add(self, interaction: discord.Interaction, btn: Button):
        await interaction.response.send_modal(AddRoleModal())

    @discord.ui.button(label="Deletar Cargo", style=discord.ButtonStyle.red, emoji=emojis.LIXO, custom_id="deletar_role")
    async def deletar(self, interaction: discord.Interaction, btn: Button):
        roles = session.query(RolesMMR).all()
        if roles:
            sucess = Embed(
                title=f"{emojis.SUCESS} | Selecione um cargo para deletar:",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=sucess, view=RoleSelectDeleteView(roles), ephemeral=True)
        else:
            failed = Embed(
                title=f"{emojis.FAILED} | Nenhum cargo registrado!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=failed, ephemeral=True)

    @discord.ui.button(label="Editar Cargo", style=discord.ButtonStyle.green, emoji=emojis.CONFIG, custom_id="edit_role")
    async def edit(self, interaction: discord.Interaction, btn: Button):
        roles = session.query(RolesMMR).all()
        if roles:
            sucess = Embed(
                title=f"{emojis.SUCESS} | Selecione um cargo para editar:",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=sucess, view=RoleSelectEditView(roles), ephemeral=True)
        else:
            failed = Embed(
                title=f"{emojis.FAILED} | Nenhum cargo registrado!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=failed, ephemeral=True)
    
    @discord.ui.button(label="Ver Informações De Um Cargo", style=discord.ButtonStyle.green, emoji=emojis.PAPEL, custom_id="ver_role")
    async def ver(self, interaction: discord.Interaction, btn: Button):
        roles = session.query(RolesMMR).all()
        if roles:
            sucess = Embed(
                title=f"{emojis.SUCESS} | Selecione um cargo para ver as informações:",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=sucess, view=RoleSelectVerView(roles), ephemeral=True)
        else:
            failed = Embed(
                title=f"{emojis.FAILED} | Nenhum cargo registrado!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=failed, ephemeral=True)

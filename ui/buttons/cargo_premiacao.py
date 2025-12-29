import discord, emojis
from discord import Embed
from discord.ui import View, Button, Modal, TextInput
from db import session, Guild_Config, CargosPremiacao


class AddCargoModal(Modal, title="Adicionar Cargo de Premiação"):
    role_id = TextInput(label="ID do cargo:", placeholder="123456789", required=True)

    def __init__(self):
        super().__init__(timeout=None)

    async def on_submit(self, interaction: discord.Interaction):
        guild = session.query(Guild_Config).filter_by(guild_id=interaction.guild.id).first()
        if guild:
            role_id = 0
            try:
                role_id = int(self.role_id.value)
            except:
                failed = Embed(
                    title=f"{emojis.FAILED} | O ID do cargo precisa ser um número!",
                    color=discord.Color.red()
                )
                return await interaction.response.send_message(embed=failed, ephemeral=True)

            # Verificar se cargo já está cadastrado
            cargo_db = session.query(CargosPremiacao).filter_by(
                guild_id=interaction.guild.id, role_id=role_id
            ).first()

            if not cargo_db:
                role = interaction.guild.get_role(role_id)
                if role:
                    add_cargo = CargosPremiacao(interaction.guild.id, role_id, role.name)
                    session.add(add_cargo)
                    session.commit()

                    sucess = Embed(
                        title=f"{emojis.SUCESS} | Cargo de premiação adicionado!",
                        color=discord.Color.green()
                    )
                    sucess.add_field(name="Cargo:", value=role.mention)
                    await interaction.response.send_message(embed=sucess, ephemeral=True)
                else:
                    failed = Embed(
                        title=f"{emojis.FAILED} | Cargo não encontrado no servidor!",
                        color=discord.Color.red()
                    )
                    await interaction.response.send_message(embed=failed, ephemeral=True)
            else:
                failed = Embed(
                    title=f"{emojis.FAILED} | Este cargo já está cadastrado!",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=failed, ephemeral=True)
        else:
            failed = Embed(
                title=f"{emojis.FAILED} | Servidor não está configurado!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=failed, ephemeral=True)


class CargoSelectDelete(discord.ui.Select):
    def __init__(self, cargos, guild):
        self.guild = guild
        options = []
        for cargo in cargos[:25]:
            role = guild.get_role(cargo.role_id)
            label = role.name if role else cargo.role_name
            options.append(discord.SelectOption(label=label[:100], value=str(cargo.role_id)))

        super().__init__(
            placeholder="Selecione um cargo para remover:",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        role_id = int(self.values[0])
        cargo = session.query(CargosPremiacao).filter_by(
            guild_id=interaction.guild.id, role_id=role_id
        ).first()

        if cargo:
            nome = cargo.role_name
            session.delete(cargo)
            session.commit()

            deleted = Embed(
                title=f"{emojis.LIXO} | Cargo removido!",
                description=f"O cargo **{nome}** foi removido da lista de premiações.",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=deleted, ephemeral=True)
        else:
            failed = Embed(
                title=f"{emojis.FAILED} | Cargo não encontrado!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=failed, ephemeral=True)


class CargoSelectDeleteView(View):
    def __init__(self, cargos, guild):
        super().__init__(timeout=180)
        self.add_item(CargoSelectDelete(cargos, guild))


class ConfigCargoPremiacaoView(View):
    def __init__(self):
        super().__init__(timeout=180)

    @discord.ui.button(label="Adicionar Cargo", style=discord.ButtonStyle.green, emoji="➕")
    async def adicionar(self, interaction: discord.Interaction, btn: Button):
        await interaction.response.send_modal(AddCargoModal())

    @discord.ui.button(label="Remover Cargo", style=discord.ButtonStyle.red, emoji="➖")
    async def remover(self, interaction: discord.Interaction, btn: Button):
        cargos = session.query(CargosPremiacao).filter_by(guild_id=interaction.guild.id).all()

        if cargos:
            embed = Embed(
                title="➖ Remover Cargo de Premiação",
                description="Selecione o cargo que deseja remover:",
                color=discord.Color.red()
            )
            await interaction.response.send_message(
                embed=embed,
                view=CargoSelectDeleteView(cargos, interaction.guild),
                ephemeral=True
            )
        else:
            failed = Embed(
                title=f"{emojis.FAILED} | Nenhum cargo cadastrado!",
                description="Adicione cargos de premiação primeiro.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=failed, ephemeral=True)

    @discord.ui.button(label="Ver Cargos", style=discord.ButtonStyle.blurple, emoji="📋")
    async def listar(self, interaction: discord.Interaction, btn: Button):
        cargos = session.query(CargosPremiacao).filter_by(guild_id=interaction.guild.id).all()

        if cargos:
            embed = Embed(
                title="📋 Cargos de Premiação Cadastrados",
                color=discord.Color.blurple()
            )

            lista = ""
            for cargo in cargos:
                role = interaction.guild.get_role(cargo.role_id)
                if role:
                    lista += f"• {role.mention}\n"
                else:
                    lista += f"• ~~{cargo.role_name}~~ (cargo deletado)\n"

            embed.description = lista if lista else "Nenhum cargo cadastrado."
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            failed = Embed(
                title=f"{emojis.FAILED} | Nenhum cargo cadastrado!",
                description="Use o botão **Adicionar Cargo** para cadastrar cargos de premiação.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=failed, ephemeral=True)

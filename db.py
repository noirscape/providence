from sqlalchemy import Column, BigInteger, ForeignKey, String, DateTime, JSON, Boolean, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

# Message stuff

MAX_MESSAGE_LENGTH = 2000
MAX_FILENAME_LENGTH = 300
MAX_TOPIC_LENGTH = 1024
MAX_URL_LENGTH = 2000
MAX_NAME_LENGTH = 100
MAX_USERNAME_LENGTH = 32


class User(Base):
    __tablename__ = "users"
    id = Column(BigInteger, primary_key=True, autoincrement=False)
    name = Column(String(MAX_USERNAME_LENGTH), nullable=False)
    discriminator = Column(BigInteger, nullable=False)
    is_bot = Column(Boolean, nullable=False)
    avatar = Column(String(MAX_URL_LENGTH))
    created_at = Column(DateTime, nullable=False)
    last_updated = Column(DateTime, nullable=False)
    localized_avatar = Column(Boolean, nullable=False)


class Guild(Base):
    __tablename__ = "guilds"
    id = Column(BigInteger, primary_key=True, autoincrement=False)
    name = Column(String(MAX_NAME_LENGTH), nullable=False)
    icon_url = Column(String(MAX_URL_LENGTH))
    localized_url = Column(Boolean, nullable=False)
    owner_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    owner = relationship(User)
    created_at = Column(DateTime, nullable=False)
    last_updated = Column(DateTime, nullable=False)


class Role(Base):
    __tablename__ = "roles"
    id = Column(BigInteger, primary_key=True, autoincrement=False)
    guild_id = Column(BigInteger, ForeignKey("guilds.id"))
    guild = relationship(Guild)
    name = Column(String(MAX_NAME_LENGTH), nullable=False)
    created_at = Column(DateTime, nullable=False)


class GuildMember(Base):
    __tablename__ = "guild_members"
    __table_args__ = (
        UniqueConstraint('user_id', 'guild_id', name='unique_guild_and_id'),
    )
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    user = relationship(User)
    guild_id = Column(BigInteger, ForeignKey("guilds.id"), nullable=False)
    guild = relationship(Guild)
    id = Column(BigInteger, autoincrement=True, primary_key=True, unique=True)
    nickname = Column(String(MAX_USERNAME_LENGTH))
    last_updated = Column(DateTime, nullable=False)


class GuildChannel(Base):
    __tablename__ = "guild_channels"
    id = Column(BigInteger, primary_key=True, autoincrement=False)
    guild_id = Column(BigInteger, ForeignKey("guilds.id"), nullable=False)
    guild = relationship(Guild)
    name = Column(String(MAX_NAME_LENGTH), nullable=False)
    topic = Column(String(MAX_TOPIC_LENGTH))
    created_at = Column(DateTime, nullable=False)
    last_updated = Column(DateTime, nullable=False)


class GuildChannelEdit(Base):
    __tablename__ = "guild_channel_edits"
    edit_id = Column(BigInteger, primary_key=True, autoincrement=True)
    guild_channel_id = Column(BigInteger, ForeignKey("guild_channels.id"), nullable=False)
    guild_channel = relationship(GuildChannel)
    name = Column(String(MAX_NAME_LENGTH))
    topic = Column(String(MAX_TOPIC_LENGTH))
    edit_time = Column(DateTime, nullable=False)


class GuildMessage(Base):
    __tablename__ = "guild_messages"
    id = Column(BigInteger, primary_key=True, autoincrement=False)
    channel_id = Column(BigInteger, ForeignKey("guild_channels.id"), nullable=False)
    channel = relationship(GuildChannel)
    author_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    author = relationship(User)
    content = Column(String(MAX_MESSAGE_LENGTH))
    embed = Column(JSON)
    created_at = Column(DateTime, nullable=False)


class GuildChannelPins(Base):
    __tablename__ = "guild_channel_pins"
    pin_id = Column(BigInteger, primary_key=True, autoincrement=True)
    guild_channel_id = Column(BigInteger, ForeignKey("guild_channels.id"), nullable=False)
    channel = relationship(GuildChannel)
    message_id = Column(BigInteger, ForeignKey("guild_messages.id"), nullable=False)
    message = relationship(GuildMessage)
    is_pinned = Column(Boolean, nullable=False)
    pinned_at = Column(DateTime, nullable=False)
    unpinned_at = Column(DateTime)


class GuildEdit(Base):
    __tablename__ = "guild_edits"
    edit_id = Column(BigInteger, primary_key=True, autoincrement=True)
    guild_id = Column(BigInteger, ForeignKey("guilds.id"), nullable=False)
    guild = relationship(Guild)
    name = Column(String(MAX_NAME_LENGTH))
    owner_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    owner = relationship(User)
    edit_time = Column(DateTime, nullable=False)
    icon_url = Column(String(MAX_URL_LENGTH))
    localized_url = Column(Boolean, nullable=False)


class GuildMemberEdit(Base):
    __tablename__ = "guild_member_edit"
    member_id = Column(BigInteger, ForeignKey("guild_members.id"))
    member = relationship(GuildMember)
    nickname = Column(String(MAX_USERNAME_LENGTH))
    edit_time = Column(DateTime, nullable=False)
    edit_id = Column(BigInteger, primary_key=True, autoincrement=True)


class GuildMemberRoles(Base):
    __tablename__ = "guild_member_roles"
    member_id = Column(BigInteger, ForeignKey("guild_members.id"), primary_key=True)
    member = relationship(GuildMember)
    role_id = Column(BigInteger, ForeignKey("roles.id"), primary_key=True)
    role = relationship(Role)


class GuildMessageAttachments(Base):
    __tablename__ = "guild_message_attachments"
    attachment_id = Column(BigInteger, primary_key=True)
    message_id = Column(BigInteger, ForeignKey("guild_messages.id"))
    message = relationship(GuildMessage)
    filename = Column(String(MAX_FILENAME_LENGTH), nullable=False)
    url = Column(String(MAX_URL_LENGTH))
    filesize = Column(BigInteger)
    localized_url = Column(Boolean, nullable=False)


class GuildMessageDeletion(Base):
    __tablename__ = "guild_message_deletions"
    message_id = Column(BigInteger, ForeignKey("guild_messages.id"), primary_key=True)
    message = relationship(GuildMessage)
    deletion_time = Column(DateTime, nullable=False)


class GuildMessageEdit(Base):
    __tablename__ = "guild_message_edits"
    edit_id = Column(BigInteger, primary_key=True, autoincrement=True)
    message_id = Column(BigInteger, ForeignKey("guild_messages.id"), nullable=False)
    message = relationship(GuildMessage)
    content = Column(String(MAX_MESSAGE_LENGTH))
    embed = Column(JSON)
    edit_time = Column(DateTime, nullable=False)


class DMChannel(Base):
    __tablename__ = "dm_channels"
    id = Column(BigInteger, primary_key=True)
    remote_user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    remote_user = relationship(User)


class PrivateMessage(Base):
    __tablename__ = "dm_messages"
    id = Column(BigInteger, primary_key=True, autoincrement=False)
    channel_id = Column(BigInteger, ForeignKey("dm_channels.id"), nullable=False)
    channel = relationship(DMChannel)
    author_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    author = relationship(User)
    content = Column(String(MAX_MESSAGE_LENGTH))
    embed = Column(JSON)
    created_at = Column(DateTime, nullable=False)


class DMChannelPins(Base):
    __tablename__ = "dm_channel_pins"
    pin_id = Column(BigInteger, primary_key=True, autoincrement=True)
    dm_channel_id = Column(BigInteger, ForeignKey("dm_channels.id"), nullable=False)
    dm_channel = relationship(DMChannel)
    message_id = Column(BigInteger, ForeignKey("dm_messages.id"), nullable=False)
    message = relationship(PrivateMessage)
    is_pinned = Column(Boolean, nullable=False)
    pinned_at = Column(DateTime, nullable=False)
    unpinned_at = Column(DateTime)


class PrivateMessageAttachments(Base):
    __tablename__ = "dm_message_attachments"
    attachment_id = Column(BigInteger, primary_key=True)
    message_id = Column(BigInteger, ForeignKey("dm_messages.id"))
    message = relationship(PrivateMessage)
    filename = Column(String(MAX_FILENAME_LENGTH), nullable=False)
    url = Column(String(MAX_URL_LENGTH))
    filesize = Column(BigInteger)
    localized_url = Column(Boolean, nullable=False)


class PrivateMessageDeletion(Base):
    __tablename__ = "dm_message_deletions"
    message_id = Column(BigInteger, ForeignKey("dm_messages.id"), primary_key=True)
    message = relationship(PrivateMessage)
    deletion_time = Column(DateTime, nullable=False)


class PrivateMessageEdit(Base):
    __tablename__ = "dm_message_edits"
    edit_id = Column(BigInteger, primary_key=True, autoincrement=True)
    message_id = Column(BigInteger, ForeignKey("dm_messages.id"), nullable=False)
    message = relationship(PrivateMessage)
    content = Column(String(MAX_MESSAGE_LENGTH))
    embed = Column(JSON)
    edit_time = Column(DateTime, nullable=False)


class RoleAudit(Base):
    __tablename__ = "role_audit"
    audit_id = Column(BigInteger, primary_key=True, autoincrement=True)
    role_id = Column(BigInteger, ForeignKey("roles.id"), nullable=False)
    role = relationship(Role)
    member_id = Column(BigInteger, ForeignKey("guild_members.id"), nullable=False)
    member = relationship(GuildMember)
    role_was_added = Column(Boolean, nullable=False)
    event_at = Column(DateTime)


class RoleEdit(Base):
    __tablename__ = "role_edits"
    role_id = Column(BigInteger, ForeignKey("roles.id"), autoincrement=False)
    role = relationship(Role)
    edit_id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(MAX_NAME_LENGTH), nullable=False)
    edit_time = Column(DateTime, nullable=False)


class UserEdit(Base):
    __tablename__ = "user_edits"
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    user = relationship(User)
    edit_id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(MAX_NAME_LENGTH), nullable=False)
    discriminator = Column(BigInteger, nullable=False)
    avatar = Column(String(MAX_URL_LENGTH), nullable=False)
    edit_time = Column(DateTime, nullable=False)
    localized_avatar = Column(Boolean, nullable=False)


class BanAudit(Base):
    __tablename__ = "ban_audit"
    audit_id = Column(BigInteger, primary_key=True, autoincrement=True)
    member_id = Column(BigInteger, ForeignKey("guild_members.id"), nullable=False)
    member = relationship(GuildMember)
    member_was_banned = Column(Boolean, nullable=False)
    event_at = Column(DateTime)


class JoinLeaveAudit(Base):
    __tablename__ = "guild_join_guild_leave_audit"
    audit_id = Column(BigInteger, primary_key=True, autoincrement=True)
    guild_id = Column(BigInteger, ForeignKey("guilds.id"), nullable=False)
    guild = relationship(Guild)
    member_id = Column(BigInteger, ForeignKey("guild_members.id"), nullable=False)
    member = relationship(GuildMember)
    member_joined = Column(Boolean, nullable=False)
    event_at = Column(DateTime)

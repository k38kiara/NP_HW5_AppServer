from peewee import *


db = SqliteDatabase('database.db')
db.pragma('foreign_keys', 1)


class BaseModel(Model):
    class Meta:
        database = db


class User(BaseModel):
    username = CharField(unique=True)
    password = CharField()


class Invitation(BaseModel):
    inviter = ForeignKeyField(User, on_delete='CASCADE', related_name='inviter_invitation')
    invitee = ForeignKeyField(User, on_delete='CASCADE', related_name='invitee_invitation')


class Friend(BaseModel):
    user = ForeignKeyField(User, on_delete='CASCADE', related_name='user_friend')
    friend = ForeignKeyField(User, on_delete='CASCADE', related_name='friend_friend')


class Post(BaseModel):
    user = ForeignKeyField(User, on_delete='CASCADE', related_name='user_post')
    message = CharField()


class Token(BaseModel):
    token = CharField(unique=True)
    owner = ForeignKeyField(User, on_delete='CASCADE', related_name='owner_token')
    channel = CharField(unique=True)


class Group(BaseModel):
    name = CharField(unique=True)
    channel = CharField(unique=True)


class GroupMember(BaseModel):
    group = ForeignKeyField(Group, on_delete='CASCADE', related_name='group_groupmember')
    member = ForeignKeyField(User, on_delete='CASCADE', related_name='member_groupmember')


def initial_db():
    db.create_tables([User, Invitation, Friend, Post, Token, Group, GroupMember])

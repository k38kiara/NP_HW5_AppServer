import sys
import socket
from model import *
from playhouse.shortcuts import model_to_dict, dict_to_model
import json
import uuid
import stomp


class DBControl(object):
    def __init__(self, mq_ip='3.16.206.199', mq_port=61613):
        try:
            self.mq = stomp.Connection([(mq_ip, mq_port)])
            self.mq.start()
            self.mq.connect(wait=True)
            self.model_list = [User, Token, Invitation, Friend, Post, GroupMember, Group]
        except Exception as e:
            print(e, file=sys.stderr)

    def __connenct_db(self, send_type, func, data, return_type):
        cmd = {'type': send_type, 'func': func, 'data': data}
        print('send command to db server:', cmd)
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            s.connect(('3.16.206.199', 10009))
            s.send(json.dumps(cmd).encode())
            resp = json.loads(s.recv(8192).decode())

            data = None

            if resp['status'] == 0:

                if return_type in self.model_list:
                    data = dict_to_model(return_type, resp['result']) if resp['result'] else None
                elif type(return_type) == list:
                    data = [dict_to_model(return_type[0], r) for r in resp['result']]
                else:
                    data = resp['result']

                print('receive db server data:', data, '\n')

            else:
                print('[Error] Send SQL Error')

            return data

        except Exception as e:
            print(e, file=sys.stderr)

    def validate_token(self, token=None, *args):
        if token:
            t = self.__connenct_db(send_type='Token',
                                   func='get_or_none',
                                   data={'token': token},
                                   return_type=Token)
            if t:
                return t
        return None

    def not_login_yet(self):
        return {
            'status': 1,
            'message': 'Not login yet'
        }

    def invite(self, token=None, username=None, *args):
        token = self.validate_token(token, *args)
        if not token:
            return self.not_login_yet()

        if not username or args:
            return {
                'status': 1,
                'message': 'Usage: invite <user> <id>'
            }
        if username == token.owner.username:
            return {
                'status': 1,
                'message': 'You cannot invite yourself'
            }
        friend = self.__connenct_db('User', 'get_or_none', {'username': username}, User)
        if friend:
            res1 = self.__connenct_db('Friend', 'get_or_none', {'user': model_to_dict(token.owner),
                                                                'friend': model_to_dict(friend),
                                                                'flag': 0}, Friend)
            res2 = self.__connenct_db('Friend', 'get_or_none', {'friend': model_to_dict(token.owner),
                                                                'user': model_to_dict(friend),
                                                                'flag': 0}, Friend)
            if res1 or res2:
                return {
                    'status': 1,
                    'message': '{} is already your friend'.format(username)
                }
            else:
                invite1 = self.__connenct_db('Invitation', 'get_or_none',
                                             {'inviter': model_to_dict(token.owner),
                                              'invitee': model_to_dict(friend)}, Invitation)
                invite2 = self.__connenct_db('Invitation', 'get_or_none',
                                             {'invitee': model_to_dict(token.owner),
                                              'inviter': model_to_dict(friend)}, Invitation)
                if invite1:
                    return {
                        'status': 1,
                        'message': 'Already invited'
                    }
                elif invite2:
                    return {
                        'status': 1,
                        'message': '{} has invited you'.format(username)
                    }
                else:
                    self.__connenct_db('Invitation', 'create', {'inviter': model_to_dict(token.owner),
                                                                'invitee': model_to_dict(friend)}, Invitation)
                    return {
                        'status': 0,
                        'message': 'Success!'
                    }
        else:
            return {
                'status': 1,
                'message': '{} does not exist'.format(username)
            }
        pass

    def list_invite(self, token=None, *args):
        token = self.validate_token(token, *args)
        if not token:
            return self.not_login_yet()

        if args:
            return {
                'status': 1,
                'message': 'Usage: list-invite <user>'
            }
        res = self.__connenct_db('Invitation', 'select', {'invitee': model_to_dict(token.owner)}, [Invitation])
        invite = []
        for r in res:
            invite.append(r.inviter.username)
        return {
            'status': 0,
            'invite': invite
        }

    def accept_invite(self, token=None, username=None, *args):
        token = self.validate_token(token, *args)
        if not token:
            return self.not_login_yet()

        if not username or args:
            return {
                'status': 1,
                'message': 'Usage: accept-invite <user> <id>'
            }
        inviter = self.__connenct_db('User', 'get_or_none', {'username': username}, User)
        invitation = self.__connenct_db('Invitation', 'get_or_none',
                                     {'inviter': model_to_dict(inviter),
                                      'invitee': model_to_dict(token.owner)}, Invitation) if inviter else None
        if invitation:
            self.__connenct_db('Friend', 'create', {'user': model_to_dict(token.owner),
                                                    'friend': model_to_dict(inviter)}, Friend)
            # Friend.create(user=token.owner, friend=inviter)

            self.__connenct_db('Invitation', 'delete_instance', {'Invitation': model_to_dict(invitation)}, None)
            # invitation.delete_instance()
            return {
                'status': 0,
                'message': 'Success!'
            }
        else:
            return {
                'status': 1,
                'message': '{} did not invite you'.format(username)
            }
        pass

    def list_friend(self, token=None, *args):
        token = self.validate_token(token, *args)
        if not token:
            return self.not_login_yet()

        if args:
            return {
                'status': 1,
                'message': 'Usage: list-friend <user>'
            }
        # friends = Friend.select().where((Friend.user == token.owner) | (Friend.friend == token.owner))
        friends = self.__connenct_db('Friend', 'select', {'user': model_to_dict(token.owner),
                                                          'friend': model_to_dict(token.owner)}, [Friend])
        res = []
        for f in friends:
            if f.user == token.owner:
                res.append(f.friend.username)
            else:
                res.append(f.user.username)
        return {
            'status': 0,
            'friend': res
        }

    def post(self, token=None, *args):
        token = self.validate_token(token, *args)
        if not token:
            return self.not_login_yet()

        if len(args) <= 0:
            return {
                'status': 1,
                'message': 'Usage: post <user> <message>'
            }
        # Post.create(user=token.owner, message=' '.join(args))
        self.__connenct_db('Post', 'create', {'user': model_to_dict(token.owner), 'message': ' '.join(args)}, Post)
        return {
            'status': 0,
            'message': 'Success!'
        }

    def receive_post(self, token=None, *args):
        token = self.validate_token(token, *args)
        if not token:
            return self.not_login_yet()

        if args:
            return {
                'status': 1,
                'message': 'Usage: receive-post <user>'
            }
        # res = Post.select().where(Post.user != token.owner) \
        #     .join(Friend, on=((Post.user == Friend.user) | (Post.user == Friend.friend))) \
        #     .where((Friend.user == token.owner) | (Friend.friend == token.owner))
        res = self.__connenct_db('Post', 'select', {'user': model_to_dict(token.owner)}, [Post])
        post = []
        for r in res:
            post.append({
                'id': r.user.username,
                'message': r.message
            })
        return {
            'status': 0,
            'post': post
        }

    def send(self, token=None, username=None, *args):
        token = self.validate_token(token, *args)
        if not token:
            return self.not_login_yet()

        if not args or not username:
            return {
                'status': 1,
                'message': 'Usage: send <user> <friend> <message>'
            }
        else:
            # user = User.get_or_none(User.username == username)
            user = self.__connenct_db('User', 'get_or_none', {'username': username}, User)
            if user:
                # friend = Friend.get_or_none(((Friend.user == token.owner) & (Friend.friend == user))
                #                             | ((Friend.friend == token.owner) & (Friend.user == user)))
                friend = self.__connenct_db('Friend', 'get_or_none', {'user': model_to_dict(token.owner),
                                                                    'friend': model_to_dict(user),
                                                                    'flag': 1}, Friend)
                if friend:
                    # t = Token.get_or_none(Token.owner == user)
                    t = self.__connenct_db('Token', 'get_or_none', {'owner': model_to_dict(user)}, Token)
                    if t:
                        msg = {
                            'type': 0,
                            'from': token.owner.username,
                            'to': user.username,
                            'message': " ".join(args)
                        }
                        self.mq.send("/queue/" + t.channel, json.dumps(msg))
                        return {
                            'status': 0,
                            'message': 'Success!'
                        }
                    else:
                        return {
                            'status': 1,
                            'message': '{} is not online'.format(username)
                        }
                else:
                    return {
                        'status': 1,
                        'message': '{} is not your friend'.format(username)
                    }
            else:
                return {
                    'status': 1,
                    'message': 'No such user exist'
                }

    def create_group(self, token=None, group_name=None, *args):
        token = self.validate_token(token, *args)
        if not token:
            return self.not_login_yet()

        if not group_name or args:
            return {
                'status': 1,
                'message': 'Usage: create-group <user> <group>'
            }
        # group = Group.get_or_none(Group.name == group_name)
        group = self.__connenct_db('Group', 'get_or_none', {'name': group_name}, Group)
        if not group:
            channel = uuid.uuid4().hex[:20].upper()
            # g = Group.create(name=group_name, member=token.owner, channel=channel)
            g = self.__connenct_db('Group', 'create', {'name': group_name,
                                                       'member': model_to_dict(token.owner),
                                                       'channel': channel}, Group)

            # GroupMember.create(group=g, member=token.owner)
            self.__connenct_db('GroupMember', 'create', {'group': model_to_dict(g),
                                                         'member': model_to_dict(token.owner)}, GroupMember)
            return {
                'status': 0,
                'message': 'Success!',
                'channel': channel
            }
        else:
            return {
                'status': 1,
                'message': '{} already exist'.format(group_name)
            }

    def list_group(self, token=None, *args):
        token = self.validate_token(token, *args)
        if not token:
            return self.not_login_yet()

        if args:
            return {
                'status': 1,
                'message': 'Usage: list-group <user>'
            }
        # groups = Group.select()
        groups = self.__connenct_db('Group', 'select', {}, [Group])
        res = []
        for g in groups:
            res.append(g.name)
        return {
            'status': 0,
            'group': res
        }

    def list_joined(self, token=None, *args):
        token = self.validate_token(token, *args)
        if not token:
            return self.not_login_yet()

        if args:
            return {
                'status': 1,
                'message': 'Usage: list-joined <user>'
            }
        # groups = GroupMember.select().where(GroupMember.member == token.owner)
        groups = self.__connenct_db('GroupMember', 'select', {'member': model_to_dict(token.owner)}, [GroupMember])

        res = []
        for g in groups:
            res.append(g.group.name)
        return {
            'status': 0,
            'group': res
        }

    def join_group(self, token=None, group_name=None, *args):
        token = self.validate_token(token, *args)
        if not token:
            return self.not_login_yet()

        if not group_name or args:
            return {
                'status': 1,
                'message': 'Usage: join-group <user> <group>'
            }
        # group = Group.get_or_none(Group.name == group_name)
        group = self.__connenct_db('Group', 'get_or_none', {'name': group_name}, Group)
        if group:
            # added = GroupMember.select().where((GroupMember.group == group) & (GroupMember.member == token.owner))
            added = self.__connenct_db('GroupMember', 'select', {'member': model_to_dict(token.owner),
                                                                 'group': model_to_dict(group)}, [GroupMember])
            if not added:
                # GroupMember.create(group=group, member=token.owner)
                self.__connenct_db('GroupMember', 'create', {'group': model_to_dict(group),
                                                             'member': model_to_dict(token.owner)}, GroupMember)
                return {
                    'status': 0,
                    'message': 'Success!',
                    'channel': group.channel
                }
            else:
                return {
                    'status': 1,
                    'message': 'Already a member of {}'.format(group_name)
                }
        else:
            return {
                'status': 1,
                'message': '{} does not exist'.format(group_name)
            }

    def send_group(self, token=None, group_name=None, *args):
        token = self.validate_token(token, *args)
        if not token:
            return self.not_login_yet()

        if not args or not group_name:
            return {
                'status': 1,
                'message': 'Usage: send-group <user> <group> <message>'
            }
        else:
            # group = Group.get_or_none(Group.name == group_name)
            group = self.__connenct_db('Group', 'get_or_none', {'name': group_name}, Group)
            if group:
                # g = GroupMember.get_or_none((GroupMember.group == group) & (GroupMember.member == token.owner))
                g = self.__connenct_db('GroupMember', 'get_or_none',
                                       {'group': model_to_dict(group),
                                        'member': model_to_dict(token.owner)}, GroupMember)
                if g:
                    msg = {
                        'type': 1,
                        'from': token.owner.username,
                        'to': g.group.name,
                        'message': " ".join(args)
                    }
                    self.mq.send('/topic/' + g.group.channel, json.dumps(msg))
                    return {
                        'status': 0,
                        'message': 'Success!'
                    }
                else:
                    return {
                        'status': 1,
                        'message': 'You are not the member of {}'.format(group_name)
                    }
            else:
                return {
                    'status': 1,
                    'message': 'No such group exist'
                }


class Server(object):
    def __init__(self, ip, port):
        try:
            socket.inet_aton(ip)
            if 0 < int(port) < 65535:
                self.ip = ip
                self.port = int(port)
            else:
                raise Exception('Port value should between 1~65535')
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.db = DBControl()
        except Exception as e:
            print(e, file=sys.stderr)
            sys.exit(1)

    def run(self):
        self.sock.bind((self.ip, self.port))
        self.sock.listen(100)
        socket.setdefaulttimeout(3)
        while True:
            try:
                conn, addr = self.sock.accept()
                with conn:
                    cmd = conn.recv(4096).decode()
                    resp = self.__process_command(cmd)
                    conn.send(resp.encode())
            except Exception as e:
                print(e, file=sys.stderr)

    def __process_command(self, cmd):
        command = cmd.split()
        if len(command) > 0:
            command_exec = getattr(self.db, command[0].replace('-', '_'), None)
            if command_exec:
                print(command)
                return json.dumps(command_exec(*command[1:]))
        return self.__command_not_found(command[0])

    def __command_not_found(self, cmd):
        return json.dumps({
            'status': 1,
            'message': 'Unknown command {}'.format(cmd)
        })


def launch_server(ip, port):
    c = Server(ip, port)
    c.run()


if __name__ == '__main__':
    launch_server('0.0.0.0', 10008)

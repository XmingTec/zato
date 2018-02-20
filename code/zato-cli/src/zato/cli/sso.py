# -*- coding: utf-8 -*-

"""
Copyright (C) 2018, Zato Source s.r.o. https://zato.io

Licensed under LGPLv3, see LICENSE.txt for terms and conditions.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

# stdlib
import os

# Bunch
from bunch import Bunch

# Zato
from zato.cli import ManageCommand, ZatoCommand
from zato.common.crypto import CryptoManager
from zato.common.util import get_config
from zato.sso import ValidationError
from zato.sso.user import CreateUserCtx, UserAPI
from zato.sso.util import new_user_id, normalize_password_reject_list

# ################################################################################################################################

class SSOCommand(ZatoCommand):
    """ Base class for SSO-related commands.
    """
    user_required = True

    def _get_sso_config(self, args):
        repo_location = os.path.join(args.path, 'config', 'repo')
        secrets_conf = get_config(repo_location, 'secrets.conf', needs_user_config=False)

        sso_conf = get_config(repo_location, 'sso.conf', needs_user_config=False)
        normalize_password_reject_list(sso_conf)

        crypto_manager = CryptoManager.from_secret_key(secrets_conf.secret_keys.key1)
        crypto_manager.add_hash_scheme('sso.super-user', sso_conf.hash_secret.rounds_super_user, sso_conf.hash_secret.salt_size)

        server_conf = get_config(
            repo_location, 'server.conf', needs_user_config=False, crypto_manager=crypto_manager, secrets_conf=secrets_conf)

        def _get_session():
            return self.get_odb_session_from_server_config(server_conf, None)

        def _hash_secret(_secret):
            return crypto_manager.hash_secret(_secret, 'sso.super-user')

        return UserAPI(sso_conf, _get_session, crypto_manager.encrypt, crypto_manager.decrypt, _hash_secret, new_user_id)

# ################################################################################################################################

    def execute(self, args):
        user_api = self._get_sso_config(args)

        if self.user_required:
            user = user_api.get_user_by_username(args.username)
            if not user:
                self.logger.warn('No such user `%s`', args.username)
                return self.SYS_ERROR.NO_SUCH_SSO_USER
        else:
            user = None

        return self._on_sso_command(args, user, user_api)

# ################################################################################################################################

    def _on_sso_command(self, args, user, user_api):
        raise NotImplementedError('Must be implement by subclasses')

# ################################################################################################################################

class _CreateUser(SSOCommand):
    user_required = False
    create_func = None
    user_type = None

    allow_empty_secrets = True
    opts = [
        {'name': 'username', 'help': 'Username to use'},
        {'name': '--email', 'help': "Super user's email"},
        {'name': '--display-name', 'help': "Person's display name"},
        {'name': '--first-name', 'help': "Person's first name"},
        {'name': '--middle-name', 'help': "Person's middle name"},
        {'name': '--last-name', 'help': "Person's middle name"},
        {'name': '--password', 'help': 'Password'},
    ]

# ################################################################################################################################

    def _on_sso_command(self, args, user, user_api):

        if user_api.get_user_by_username(args.username):
            self.logger.warn('User already exists `%s`', args.username)
            return self.SYS_ERROR.USER_EXISTS

        try:
            user_api.validate_password(args.password)
        except ValidationError as e:
            self.logger.warn('Password validation error, reason code:`%s`', ', '.join(e.sub_status))
            return self.SYS_ERROR.VALIDATION_ERROR

        data = Bunch()
        data.username = args.username
        data.email = args.email or b''
        data.display_name = args.display_name or b''
        data.first_name = args.first_name or b''
        data.middle_name = args.middle_name or b''
        data.last_name = args.last_name or b''
        data.password = args.password

        ctx = CreateUserCtx()
        ctx.data = data

        func = getattr(user_api, self.create_func)
        func(ctx)

        self.logger.info('Created %s `%s`', self.user_type, data.username)

# ################################################################################################################################

class CreateUser(_CreateUser):
    """ Creates a new regular SSO user
    """
    create_func = 'create_user'
    user_type = 'user'

# ################################################################################################################################

class CreateSuperUser(_CreateUser):
    """ Creates a new SSO super-user
    """
    create_func = 'create_super_user'
    user_type = 'super-user'

# ################################################################################################################################

class DeleteUser(SSOCommand):
    """ Deletes an existing user from SSO (super-user or a regular one).
    """
    opts = [
        {'name': 'username', 'help': 'Username to delete'},
        {'name': '--delete-self', 'help': "Force deletion of user's own account"},
    ]

    def _on_sso_command(self, args, user, user_api):
        user_api.delete_user(username=args.username)
        self.logger.info('Deleted user `%s`', args.username)

# ################################################################################################################################

class LockUser(SSOCommand):
    """ Locks a user account. The person may not log in.
    """
    opts = [
        {'name': 'username', 'help': 'User account to lock'},
    ]

    def _on_sso_command(self, args, user, user_api):
        user_api.lock_user(user.user_id)
        self.logger.info('Locked user account `%s`', args.username)

# ################################################################################################################################

class UnlockUser(SSOCommand):
    """ Unlocks a user account
    """
    opts = [
        {'name': 'username', 'help': 'User account to unlock'},
    ]

    def _on_sso_command(self, args, user, user_api):
        user_api.unlock_user(user.user_id)
        self.logger.info('Unlocked user account `%s`', args.username)

# ################################################################################################################################

class ChangeUserPassword(SSOCommand):
    """ Changes password of a user given on input. Use reset-user-password if new password should be auto-generated.
    """
    opts = [
        {'name': 'username', 'help': 'User to change the password of'},
        {'name': '--password', 'help': 'New password'},
        {'name': '--expiry', 'help': "Password's expiry in hours or days"},
        {'name': '--must-change', 'help': "A flag indicating whether the password must be changed on next login"},
    ]

    def _on_sso_command(self, args, user, user_api):
        self.logger.info('Changed password for user `%s`', args.username)

# ################################################################################################################################

class ResetUserPassword(SSOCommand):
    """ Sets a new random for user and returns it on output. Use change-password if new password must be given on input.
    """
    opts = [
        {'name': 'username', 'help': 'User to reset the password of'},
        {'name': '--expiry', 'help': "Password's expiry in hours or days"},
        {'name': '--must-change', 'help': "A flag indicating whether the password must be changed on next login"},
    ]

    def _on_sso_command(self, args, user, user_api):
        self.logger.info('Reset password for user `%s`', args.username)

# ################################################################################################################################

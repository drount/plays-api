#! /usr/bin/env python

import os

from flask_script import Manager

from plays import create_app

app = create_app(os.getenv('APP_CONFIG', 'default'))
manager = Manager(app)


@manager.shell
def make_shell_context():
    return dict(app=app)

@manager.command
def sync():
    from plays.models import _sync_database
    _sync_database()

if __name__ == '__main__':
    manager.run()

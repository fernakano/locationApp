#! /usr/bin/env python3
# *-* coding: utf8 *-*
import yaml
import sqlite3
import os
import inspect
import sys
import time
import json
import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.auth
import tornado.options
import tornado.autoreload
import tornado.log
from tornado.options import define, options

__config__ = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))+'/app.yaml'
__ssl__ = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))+'/ssl/'

define('version', default=None, help='Version settings (default: production)')

print(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))))
conn = sqlite3.connect(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))+'/db/locations.db')


def loc_create_tables():
    conn.execute('CREATE TABLE IF NOT EXISTS logLocation ('
                 'user VARCHAR(25),'
                 'lat DECIMAL(20,17),'
                 'long DECIMAL(20,17),'
                 'time DATETIME);')


loc_create_tables()

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

class App(tornado.web.Application):
    def __init__(self, settings):
        handlers = [
            (r'/', MainHandler),
            (r'/api/?(\w*)'
             r'/?([-+]?\d*\.?\d*)'
             r'/?([-+]?\d*\.?\d*)/?.*', LocationHandler),
            (r'/getLocs', GetLocationHandler),
        ]

        tornado.web.Application.__init__(
            self,
            handlers,
            **settings
        )


class BaseHandler(tornado.web.RequestHandler):
    pass


class MainHandler(BaseHandler):
    def get(self):
        items = ["Item 1", "Item 2", "Item 3"]
        # print(dict_factory(self))
        self.render('index.html', title="My title", items=items)


class LocationHandler(BaseHandler):
    def get(self, user, lat, long):

        if user and lat and long:
            self.write({
                'status': 'ok',
                'user': user,
                'lat': lat,
                'long': long
            })
            conn.execute('INSERT INTO logLocation '
                         '(user,lat,long,time)'
                         ' VALUES '
                         '(?,?,?,?);', (user, lat, long, time.strftime("%d/%m/%Y %H:%M:%S")))
            conn.commit()
        else:
            self.write({
                'status': 'not ok, Something is wrong'
            })


class GetLocationHandler(BaseHandler):
    def get(self):
        conn.row_factory = dict_factory
        cursor = conn.cursor()
        cursor.execute("select user,lat,long,time from logLocation order by time DESC")

        self.write(json.dumps(cursor.fetchall(), sort_keys=True))


if __name__ == '__main__':
    tornado.options.parse_command_line()

    # Try to load the Configuration File, If itis not Present Throw an Error.
    try:
        f = open(__config__, 'r')
        config = yaml.load(f)
        f.close()
    except IOError:
        print('Invalid or missing config file %s' % __config__)
    else:
        # if no settings is present in the file, we go away
        if 'settings' not in config:
            print('No default configuration found')
            sys.exit(1)

        # Check Environment option is setup.
        if options.version and options.version in config['extra_settings']:
            settings = dict(
                config['settings'],
                **config['extra_settings'][options.version]
            )
        else:
            settings = config['settings']

        # Set Base Path for configured directories
        for k, v in settings.items():
            if k.endswith('_path'):
                settings[k] = settings[k].replace(
                    '__path__',
                    os.path.dirname(__file__)
                )

        http_server = tornado.httpserver.HTTPServer(App(settings),ssl_options={
        "certfile": __ssl__+"iplocationapp.crt",
        "keyfile": __ssl__+"iplocationapp.key",
    })
        http_server.listen(config['port'])

        # Set Debug mode ON.
        if 'debug' in settings and settings['debug'] is True:
            tornado.autoreload.start()

        tornado.log.enable_pretty_logging()
        tornado.ioloop.IOLoop.instance().start()

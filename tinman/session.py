#!/usr/bin/env python
"""
Tinman Session Handler
"""

__author__  = "Gavin M. Roy"
__email__   = "gavinmroy@gmail.com"
__date__    = "2010-03-09"
__version__ = 0.1

import datetime
import hashlib
import logging
import os
import pickle

class Session:

    # List of attributes to not store in session dictionary
    protected = ['id', 'handler', 'path', 'protected', 'settings', 'values']

    # Empty session dictionary
    values = {}

    def __init__(self, handler):

        logging.debug('Session object initialized')

        # Carry the handler object for access to settings and cookies
        self.handler = handler

        # Make sure there are session settings
        if handler.application.settings.has_key('Session'):
            self.settings = handler.application.settings['Session']
        else:
            raise Exception('Application settings are missing the Session entries')

        # If our storage type is file, set the base path for the session file
        if self.settings['type'] == 'file':
            self.path = self.settings['directory'].replace('__base_path__',
                                                           handler.application.settings['base_path'])

        # Try and get the current session
        self.id = self.handler.get_secure_cookie(self.settings['cookie_name'])

        # If we have one, try and load the values, otherwise start a new session
        if self.id:
            self._load()
        else:
            self.id = self._new()

    def __delattr__(self, key):

        # If our key is not in our protected list, try and remove it from the session dict
        if key not in self.protected:
            logging.debug('Removing "%s" from the session dictionary' % key)
            if self.values.has_key(key):
                del(self.values[key])
        else:
            # For some reason we want to remove this, so allow it
            del(self.__dict__[key])

    def __setattr__(self, key, value):

        # If our key is not in our protected list, try and remove it from the session dict
        if key not in self.protected:
            logging.debug('Adding "%s" to the session dictionary' % key)
            self.values[key] = value
        else:
            # Set the attribute in the object dict
            self.__dict__[key] = value

    def __getattr__(self, key, type=None):

        if key not in self.protected:
            if self.values.has_key(key):
                return self.values[key]
        else:
            return self.__dict__[key]
        return None

    def _load(self):

        # If we're storing using files
        if self.settings['type'] == 'file':

            # Create the full path to the session file
            session_file = '/'.join([self.path, self.id])
            logging.debug('Loading contents of session file: %s' % session_file)
            try:
                with open(session_file, 'r') as f:
                    self.values = pickle.loads(f.read())
                f.closed
            except IOError:
                logging.info('Missing session file for session %s, creating new with same id' % self.id)

                # Set the session start time
                self.started = datetime.datetime.now()

                # Save the initial session
                self.save()

    def _new(self):
        """ Create a new session ID and set the session cookie """
        # Create a string we can hash that should be fairly unique to the request
        s = ':'.join([self.handler.request.remote_ip,
                      self.handler.request.headers['User-Agent'],
                      datetime.datetime.today()])

        # Build the sha1 based session id
        h = hashlib.sha1()
        h.update(s)
        id = h.hexdigest()

        # Send the cookie
        self.handler.set_secure_cookie( self.settings['cookie_name'],
                                        id,
                                        self.settings['duration'])

        # Set the session start time
        self.started = datetime.datetime.now()

        # Save the initial session
        self.save()

        # Return the session id
        return id

    def clear(self):

        # Clear the session cookie
        self.handler.clear_cookie(self.settings['cookie_name'])

        # If we're storing with files
        if self.settings['type'] == 'file':

            # Create the full path to the session file
            session_file = '/'.join([self.path, self.id])
            logging.debug('Removing cleared session file: %s' % session_file)

            # Unlink the file
            os.unlink(session_file)

        # Remove the id
        del(self.id)

    def save(self):

        # If we're storing using files
        if self.settings['type'] == 'file':

            # Create the full path to the session file
            session_file = '/'.join([self.path, self.id])
            logging.debug('Writing contents of session file: %s' % session_file)
            try:
                with open(session_file, 'w') as f:
                    f.write(pickle.dumps(self.values))
                f.closed
            except IOError:
                logging.error('Could not write to session file: %s' % session_file)
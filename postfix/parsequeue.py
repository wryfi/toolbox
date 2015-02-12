#!/usr/bin/env python

'''
This module parses postfix queue data into useful python objects. Each message
is stored as a QueuedMessage object, with delete(), hold(), and release()
methods for performing these frequently used queue operations. A Queue object
parses the queue data and includes a list of QueuedMessage objects in its
queuedMessages attribute. Queue() provides a simple filter() method for filtering
queuedMessages by sender, recipient, error, or queue. 

Copyright (c) 2014, Christian Haumesser <ch@wryfi.net>
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
this list of conditions and the following disclaimer in the documentation
and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors
may be used to endorse or promote products derived from this software without
specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
'''

from datetime import datetime
import os
import re
import subprocess


class QueuedMessage(object):
  '''
  Representation of a queued message in a postfix queue
  '''
  def __init__(self, sender=None, recipient=None, time=None, queueId=None, size=None, error=None, queue=None):
    self.sender = sender
    self.recipient = recipient
    self.time = time
    self.queueId = queueId
    self.size = size
    self.error = error
    self.queue = queue

  def delete(self):
    if self.queueId:
      print('deleting %s from %s queue' % (self.queueId, self.queue))
      try:
        subprocess.check_call(['postsuper', '-d', self.queueId], stdout=subprocess.PIPE)
      except Exception as ex:
        raise RuntimeError('an error occurred attempting to remove the queued message')

  def hold(self):
    if self.queueId and self.queue != 'hold':
      try:
        subprocess.check_call(['postsuper', '-h', self.queueId])
      except Exception as ex:
        raise RuntimeError('an error occurred trying to hold the selected message')

  def release(self):
    if self.queueId and self.queue == 'hold':
      try:
        subprocess.check_call(['postsuper', '-H', self.queueId])
      except Exception as ex:
        raise RuntimeError('an error occurred trying to release the selected message')


class Queue(object):
  '''
  Object representing a postfix queue. By default, reads queue from 'postqueue -p'
  command output. To read a queue saved to a text file, pass 
  datasource='/path/to/file'. Queued messages are represented as QueuedMeessage
  objects and stored as a list in Queue.queuedMessages.
  '''
  def __init__(self, datasource='postqueue'):
    if datasource == 'postqueue':
      try:
        getQueue = subprocess.Popen(['postqueue', '-p'], stdout=subprocess.PIPE)
        self.rawQueueData = getQueue.communicate()[0]
      except Exception as ex:
        raise RuntimeError('unable to retrieve queue data from postqueue: %s' % ex)
    else:
      if os.path.isfile(datasource):
        with open(datasource, 'rb') as qfile:
          self.rawQueueData = qfile.read()
      else:
        raise RuntimeError('datasource parameter must be a valid file containing postqueue output')
    self.queueData = self.rawQueueData.decode().split('\n\n')
    # the first queue entry contains a header line that needs to be removed
    self.queueData[0] = '\n'.join(self.queueData[0].split('\n')[1:])
    # the last line of postqueue output is a footer that needs to be removed
    self.queueData.pop(len(self.queueData) - 1)
    self.queuedMessages = []
    for message in self.queueData:
      queuedMessage = QueuedMessage()
      parts = message.split('\n')
      sentInfo = parts[0]
      # in addition to stripping whitespace, remove enclosing parentheses
      queuedMessage.error = parts[1].strip()[1:-1]
      queuedMessage.recipient = parts[2].strip()
      sentRegex = r'([A-F0-9]*)([\*!]*)\s*([0-9]*)\s*(\w{3})\s(\w{3})\s+(\d{1,2})\s(\d{2}):(\d{2}):(\d{2})\s*([A-Za-z0-9.@\-_+]*)'
      sentInfoMatch = re.match(sentRegex, sentInfo)
      queuedMessage.queueId = sentInfoMatch.groups()[0]
      if sentInfoMatch.groups()[1] == '':
        queuedMessage.queue = 'deferred'
      elif sentInfoMatch.groups()[1] == '!':
        queuedMessage.queue = 'hold'
      elif sentInfoMatch.groups()[1] == '*':
        queuedMessage.queue = 'active'
      queuedMessage.size = sentInfoMatch.groups()[2]
      datestring = ' '.join([
          sentInfoMatch.groups()[4], 
          sentInfoMatch.groups()[5],
          # postqueue doesn't provide a year, so assume dates are in the current year
          str(datetime.utcnow().year),
          sentInfoMatch.groups()[6],
          sentInfoMatch.groups()[7],
          sentInfoMatch.groups()[8]
      ])
      queuedMessage.time = datetime.strptime(datestring, '%b %d %Y %H %M %S')
      queuedMessage.sender = sentInfoMatch.groups()[9]
      self.queuedMessages.append(queuedMessage)

  def filter(self, parameter, value):
    '''
    Filter queued messages by parameter (must be one of 'sender', 'recipient', 
    'error', 'queue') and value, where value is a string or regular expression 
    (raw string), to match the parameter against.
    '''
    filtered = []
    if parameter not in ['sender', 'recipient', 'error', 'queue']:
      raise RuntimeError('invalid filter parameter')
    for message in self.queuedMessages:
      if re.match(value, getattr(message, parameter)):
        filtered.append(message)
    return filtered

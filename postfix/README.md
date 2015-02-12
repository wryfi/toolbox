# parsequeue

A mail account with a weak password was recently compromised on one of my mail
systems, resulting in thousands of undeliverable messages in the postfix queue,
which the system was still periodically trying to deliver. I found few easy ways
to filter and remove the offending messages, so I wrote this module.

It parses postfix queue data into useful python objects. Each message
is stored as a QueuedMessage object, with delete(), hold(), and release()
methods for performing these frequently used queue operations. A Queue object
parses the queue data and includes a list of QueuedMessage objects in its
queuedMessages attribute. Queue() provides a simple filter() method for filtering
queuedMessages by sender, recipient, error, or queue. 

## Caveats

* Requires python-2.7+
* `postqueue` datetimes do not include a year, so message times are all presumed
    to be in the current year.
* Not resilient to changes in postqueue output formatting.
* Probably needs to run as root on most systems.

## Example usage:

    from parsequeue import Queue

    queue = Queue()

    # print the queue, sender, recipient of each queued message
    for message in queue.queuedMessages:
      print(messsage.queue, message.sender, message.recipient)

    # print the error for all messages bound for gmail
    for message in queue.filter('recipient', r'.*@gmail.com'):
      print(message.error)

    # delete all queued messages destined for .ru (Russian) domains
    for message in queue.filter('recipient', r'.*@.*\.ru):
      message.delete()

    # hold queued messages to 'bob@gmail.com'
    for message in queue.filter('recipient', 'bob@gmail.com'):
      message.hold()

    # release messages to 'bob@gmail.com' that are in the held queue
    for message in queue.filter('queue', 'held'):
      if message.recipient == 'bob@gmail.com':
        message.release()

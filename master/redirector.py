#This is an optional Sauerkraut component, use if you want http traffic on
#port 80 to be redirected to https on the specified url and port of Master.
from bottle import route, run, redirect
from json import loads

@route('/')
def redirector():
    """
    Redirect to the HTTPS endpoint.

    :return: Nothing.
    """

    redirect('https://{0}:{1}/'.format(config['url'], config['port']))


@route('/<path:path>')
def redirector(path):
    """
    Redirect to the HTTPS endpoint with the given path.

    :param path: Given path.
    :return: Nothing.
    """

    redirect('https://{0}:{1}/{2}'.format(config['url'], config['port'], path))

if __name__ == '__main__':
    config = loads(open('config.json', 'r').read())
    run(host=config['host'], port=80)


from bottle import route, run, static_file
from requests import get, exceptions


server_db = [
    {'name': 'Slave 1', 'host': 'localhost', 'port': '29547'},
    {'name': 'Slave 2', 'host': 'localhost', 'port': '29548'},
    {'name': 'Slave 3', 'host': 'localhost', 'port': '29549'}]

@route('/')
def index():
    page = ''

    for server in server_db:
        try:
            health = get('http://{host}:{port}/status'.format(host=server['host'], port=server['port']), timeout=0.1).json()
            cpu = health['cpu']
            ram = health['ram']

            if cpu > 70 or ram > 70:
                icon = 'yellow.png'
            else:
                icon = 'green.png'

            page += '<h3>{name}</h3><p>CPU: {cpu}</p><p>RAM: {ram}</p>'.format(name=server['name'], cpu=str(cpu), ram=str(ram))

        except exceptions.ConnectionError:
            icon = 'red.png'
            page += '<h3>{name}</h3><p>Status: Down</p>'.format(name=server['name'])

    return page

@route('/images/<name>')
def images(name):
    return static_file(name, root='images/')

run(host='localhost', port=8883)
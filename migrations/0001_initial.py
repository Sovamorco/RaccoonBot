from json import loads
from pathlib import Path

from yoyo import step


def apply(conn):
    resources = Path('resources')
    cursor = conn.cursor()

    cursor.execute('''
CREATE TABLE cookies
(
    id      BIGINT NOT NULL
        PRIMARY KEY,
    cookies INT NOT NULL
);
''')
    try:
        cookies = loads((resources / 'cookies.json').read_text())
        for entry in cookies.values():
            cursor.execute('INSERT INTO cookies (id, cookies) VALUES (%s, %s)', [entry['id'], entry['cookies']])
    except FileNotFoundError:
        pass

    cursor.execute('''
CREATE TABLE server_data
(
    id      BIGINT                      NOT NULL
        PRIMARY KEY,
    volume  INT          DEFAULT 100 NOT NULL,
    shuffle TINYINT(1)   DEFAULT 0   NOT NULL,
    prefix  VARCHAR(255) DEFAULT '?' NOT NULL
);
''')
    try:
        prefixes = loads((resources / 'prefixes.json').read_text())
        saved = loads((resources / 'saved.json').read_text())
        for key in set(prefixes.keys()) | set(saved.keys()):
            prefix = prefixes.get(key, '?')
            saved_s = saved.get(key, {})
            volume = saved_s.get('volume', 100)
            shuffle = saved_s.get('shuffle', False)
            cursor.execute('INSERT INTO server_data (id, volume, shuffle, prefix) VALUES (%s, %s, %s, %s)',
                           [key, volume, shuffle, prefix])
    except FileNotFoundError:
        pass

    cursor.execute('''
CREATE TABLE raccoons
(
    id  INT AUTO_INCREMENT
        PRIMARY KEY,
    url VARCHAR(512) NOT NULL
);
''')
    try:
        racoons = loads((resources / 'raccoons.txt').read_text())
        for line in racoons:
            url = line.strip()
            cursor.execute('INSERT INTO raccoons (url) VALUES (%s)', [url])
    except FileNotFoundError:
        pass
    conn.commit()


def rollback(conn):
    cursor = conn.cursor()
    cursor.execute('DROP TABLE cookies')
    cursor.execute('DROP TABLE server_data')
    cursor.execute('DROP TABLE raccoons')
    conn.commit()


steps = [
    step(apply, rollback)
]

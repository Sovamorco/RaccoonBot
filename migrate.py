from yoyo import get_backend, read_migrations


def migrate(config):
    backend = get_backend('mysql://{user}:{password}@{host}:{port}/{db}'.format(**config))
    migrations = read_migrations('migrations')

    with backend.lock(120):
        backend.apply_migrations(backend.to_apply(migrations))

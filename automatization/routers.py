from database import DatabaseEngine
from api import (
    InterestsListCreateAPIService,
    InterestsDetailAPIService,
    ScoreListCreateAPIService,
    ScoreDetailAPIService
)


url_patterns = [
    (
        'api/interests',
        ('GET', 'POST'),
        lambda method, data, db: InterestsListCreateAPIService(method, db, data)
    ),
    (
        'api/interests/<int:id>',
        ('GET', 'PUT', 'DELETE'),
        lambda method, client_id, data, db: InterestsDetailAPIService(method, client_id, db, data)
    ),
    (
        'api/scores',
        ('GET', 'POST'),
        lambda method, data, db: ScoreListCreateAPIService(method, db, data)
    ),
    (
        'api/scores/<int:id>',
        ('GET', 'PUT', 'DELETE'),
        lambda method, client_id, data, db: ScoreDetailAPIService(method, client_id, db, data)
    )
]


def get_api_service(path_params: dict, method: str, db: DatabaseEngine, data: dict = None):
    url = ''
    id_key = None
    for key, path in path_params.items():
        if path.isnumeric():
            id_key = int(path)
            url += '<int:id>'
            continue
        url += f'{path}/'
    url = url.rstrip('/')

    for pattern in url_patterns:
        try:
            pattern.index(url)
            if method in pattern[1]:
                if id_key is not None:
                    return pattern[-1](method=method, client_id=id_key, data=data, db=db)
                return pattern[-1](method=method, data=data, db=db)
        except ValueError:
            continue
    return None

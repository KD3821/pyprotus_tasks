# tiny_web_framework_with_otuserver

<h1 align="center">OTUServer</h1>
<p align="center"><img src="https://img.shields.io/badge/made_by-KD3821-purple"></p>

<p>Задание: разработать веб-сервер частично реализующий протокол HTTP</p>


<ol>
<li>
Разрешается использовать библиотеки помогающие реализовать асинхронную обработку соединений, запрещается
использовать библиотеки реализующие какую-либо часть обработки HTTP. Работать с сокетами и всем прочим нужно
самостоятельно.</li>
<li>
Провести нагрузочное тестирование, проверку стабильности и корректности работы.</li>
<li>
Если сервер асинхронный, то обязательно использовать epoll (https://github.com/m13253/python-asyncore-epoll)</li>
</ol>
<b>Веб-сервер должен уметь:</b>
<ul>
<li>Масштабироваться на несколько worker'ов</li>
<li>Числов worker'ов задается аргументом командной строки -w</li>
<li>Отвечать 200, 403 или 404 на GET-запросы и HEAD-запросы</li>
<li>Отвечать 405 на прочие запросы</li>
<li>Возвращать файлы по произвольному пути в DOCUMENT_ROOT</li>
<li>Вызов /file.html должен возвращать содердимое DOCUMENT_ROOT/file.html</li>
<li>DOCUMENT_ROOT задается аргументом командной строки -r</li>
<li>Возвращать index.html как индекс директории</li>
<li>Вызов /directory/ должен возвращать DOCUMENT_ROOT/directory/index.html</li>
<li>Отвечать следующими заголовками для успешных GET-запросов: Date, Server, Content-Length, Content-Type, Connection</li>
<li>Корректный Content-Type для: .html, .css, .js, .jpg, .jpeg, .png, .gif, .swf</li>
<li>Понимать пробелы и %XX в именах файлов</li>
<li>Cам сервер в httpd.py. Это точка входа</li>
</ul>
<b>Проверить:</b>
<ul>
<li>Проходят тесты https://github.com/s-stupnikov/http-test-suite</li>
<li>http://localhost/httptest/wikipedia_russia.html корректно показывается в браузере</li>
<li>Нагрузочное тестирование: запускаем ab -n 50000 -c 100 -r http://localhost:8080/ (вместо ab можно использовать wrk)</li>
</ul>
<br>
Для выполнения задания была использована PRE-FORK модель сервера (https://github.com/sat2707/web/blob/master/tcp_servers/prefork.py)
<br>

Варианты команд запуска сервера из консоли:
<ul>
<li>python3 httpd.py</li>
<li>python3 httpd.py -config server_config.json</li>
<li>python3 httpd.py -w 10</li>
<li>python3 httpd.py -w 10 -r /home/path/to/documents</li>
</ul>
<p align="center"><img src="https://github.com/kd3821/pyprotus_tasks/blob/main/img/wrk_benchmark.png?raw=true"></p>
<br>
Для нагрузочного тестирования была использована утилита WRK
<ul>
<li>Использован docker image "williamyeh/wrk" ( docker pull williamyeh/wrk )</li>
<li>Команда запуска нагрузочного тестирования (для Ubuntu 20.04): docker run --network="host" --rm williamyeh/wrk -t4 -c10 -d10s --latency http://127.0.0.1:8080/index.html</li>
<li>Остальные тесты размещены в tests/httptest.py</li>
</ul>
<br>
Дополнительно была реализована часть веб-приложения, выполняющая роль backend REST API по аналогии со "scoring API".
<ul>
<li>В качестве БД используется SQLite и сырые SQL запросы</li>
<li>При отсутствие БД в директории на момент запуска сервера - новый файл с БД будет создан автоматически</li>
<li>2 таблицы в БД: 'interests' и 'score'</li>
<li>2 класса обработки запросов: ListCreateAPIService и DetailAPIService</li>
<li>ListCreateAPIService поддерживает HTTP-методы: GET, POST</li>
<li>DetailAPIService поддерживает HTTP-методы: GET, PUT, DELETE</li>
<li>Для работы с API необходимо добавить методы 'POST', 'PUT, 'DELETE' в ALLOWED_METHODS класса HttpRequestHandler (handlers.py)</li>
</ul>
<h3>Таблица ендпоинтов (в качестве primary key используется client_id)</h3>
<table>
<thead>
<tr>
  <th>Метод</th>
  <th>Таблица БД</th>
  <th>Операция</th>
  <th>URL</th>
</tr>
</thead>
<tbody>
<tr>
  <td>GET</td>
  <td>interests</td>
  <td>List Interests of All Clients</td>
  <td>http://127.0.0.1:8080/api/interests</td>
</tr>
<tr>
  <td>POST</td>
  <td>interests</td>
  <td>Create Client with Interests</td>
  <td>http://127.0.0.1:8080/api/interests</td>
</tr>
<tr>
  <td>GET</td>
  <td>interests</td>
  <td>Get Client's Interests</td>
  <td>http://127.0.0.1:8080/api/interests/{client_id}</td>
</tr>
<tr>
  <td>PUT</td>
  <td>interests</td>
  <td>Update Client's Interests</td>
  <td>http://127.0.0.1:8080/api/interests/{client_id}</td>
</tr>
<tr>
  <td>DELETE</td>
  <td>interests</td>
  <td>Delete Client with Interests</td>
  <td>http://127.0.0.1:8080/api/interests/{client_id}</td>
</tr>
<tr>
  <td>GET</td>
  <td>scores</td>
  <td>List Scores of All Clients</td>
  <td>http://127.0.0.1:8080/api/scores</td>
</tr>
<tr>
  <td>POST</td>
  <td>scores</td>
  <td>Create Client with Score</td>
  <td>http://127.0.0.1:8080/api/scores</td>
</tr>
<tr>
  <td>GET</td>
  <td>scores</td>
  <td>Get Client's Score</td>
  <td>http://127.0.0.1:8080/api/scores/{client_id}</td>
</tr>
<tr>
  <td>PUT</td>
  <td>scores</td>
  <td>Update Client's Score</td>
  <td>http://127.0.0.1:8080/api/scores/{client_id}</td>
</tr>
<tr>
  <td>DELETE</td>
  <td>scores</td>
  <td>Delete Client with Score</td>
  <td>http://127.0.0.1:8080/api/scores/{client_id}</td>
</tr>
</tbody>
</table>
<br>
<br>
<p align="center"><img src="https://github.com/kd3821/pyprotus_tasks/blob/main/img/create_interests_api.png?raw=true"></p>
<br>
<p align="center"><img src="https://github.com/kd3821/pyprotus_tasks/blob/main/img/create_score_api.png?raw=true"></p>
<br>
<p align="center"><img src="https://github.com/kd3821/pyprotus_tasks/blob/main/img/get_interests_detail_api.png?raw=true"></p>
<br>
Предложения для расширения функционала API:
<ul>
<li>
Реализовать базовый класс Модели сущности</li>
<li>
Вынести функционал запросов к БД в отдельный модуль</li>
<li>
Доработать пагинацию</li>
</ul>
*репозиторий содержит коллекцию Postman для тестирования API

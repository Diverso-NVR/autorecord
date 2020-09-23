# NVR Autorecord

Сервис для автоматической записи потоков с камер.

## Принцип работы

Каждые полчаса сервис выполняет следующие действия:

- Останавливает запись потоков со всех устройств и выгружает полученные записи
  (если они есть) на Google Drive в папку, соответствующую дате и времени записи.
- Начинает новую запись потоков со всех устройств.

## Структура

- **app.py** - главный класс приложения, при запуске представляет собой
  процесс-демон, с определенным интервалом перезапускающий запись
  потоков с устройств и загружающий полученные видеозаписи на Google Drive.

- **drive_api.py** - содержит функции для взаимодействия с Google Drive API.

- **startstop.py** - содержит класс, в котором определены функции
  осуществления записи и обработки потоков с IP-камер и кодеров.
  Запись и обработка потоков осуществляется при помощи инструмента FFmpeg.

- **models.py** - содержит модели MySQL-таблиц, смапленные при помощи
  ORM-библиотеки SQLAlchemy.

- **requirements.txt** - список Python-библиотек, необходимых для работы
  приложения. Получается при помощи команды `pip freeze > requirements.txt`.
  Библиотеки устанавливаются в окружение при помощи команды
  `pip install -r requirements.txt`.

- **Dockerfile** - файл конфигурации для Docker-образа приложения.
  Для сборки используется базовый образ `python:3`.

- **run_docker.sh** - shell-скрипт для запуска приложения на сервере.
  Останавливает и удаляет все предыдущие запущенные образы приложения,
  собирает новый образ и запускает используя файл окружения `.env_nvr`, который
  необходимо создать и разместить в домашней директории. В `.env_nvr` файле
  должна быть указата переменная окружения `SQLALCHEMY_DATABASE_URI`,
  представляющая собой строку для подключения ORM-библиотеки к базе данных.
  Пример: `SQLALCHEMY_DATABASE_URI=postgres://<user>:<password>@localhost/nvr`.
  Также необходимо загрузить в домашную директорию ключи для работы с API гугла.
  ВАЖНО: запускать без sudo, т.е. добавить текущего юзера в группу докера (sudo gpasswd -a \$USER docker) и перелогиниться

## Развертывание на сервере

Установить докер, ето в интеренете найти, [например](https://docs.docker.com/engine/install/ubuntu/)

Добавить пользователя в sudoers докера

```bash
sudo groupadd docker
sudo usermod -aG docker $USER
newgrp docker
```

Поставить проект с гита

```bash
git clone https://git.miem.hse.ru/nvr/autorecord.git
```

Создать файл в домашней директории для переменных окружения

```bash
vim ~/.env_nvr
```

Получить данные бд и название комнаты у разработчиков и вписать в этот файл:

```bash
SQLALCHEMY_DATABASE_URI=postgres://db_username:db_password@host:port/db_name
ROOM_NAME=room_name # Для одноплатников
```

Создать папку creds в домашней директории.
Получить токены гугла у разработчиков и поместить в эту папку

```bash
mkdir ~/creds

# Со свеого хоста
scp token*.pickle username@host_ip:/home/username/creds/
```

Запустить сервис

```bash
cd autorecord
chmod +x run_docker.sh
./run_docker.sh
```

## Авторы

[Денис Приходько](https://github.com/Burnouttt),
[Дмитрий Кудрявцев](https://github.com/kuderr)

import logging
import os
import random
import socket
import struct
import sys
import time


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)


class MySender:
    ''' Отправляет данные на сервер.'''

    MAX_SIZE = 8  # максимальный размер в гигабайтах
    MAX_BYTES = MAX_SIZE * (1024 ** 3)  # максимальный размер в байтах
    RETRY_PERIOD = 10  # интервал для повторных попыток в секундах
    DEFAULT_PORT = 1234

    def __init__(self, server_host) -> None:
        self.server_host = server_host

    def _generate_random_data(self) -> bytes:
        return os.urandom(random.randint(1, self.MAX_BYTES))

    def create_tcp_connection(self) -> int:
        data = self._generate_random_data()
        logger.info(f'Сгенерированы данные размером {len(data)} байт')
        logger.info(f'Тип данных: {type(data)}')
        if len(data) > self.MAX_BYTES:
            logger.error(f'Размер данных {len(data)} превышает максимально'
                         f'допустимый размер {self.MAX_BYTES}')
            raise ValueError(f'Размер данных {len(data)} превышает максимально'
                             f'допустимый размер {self.MAX_BYTES}')

        sent_data = 0
        # Реализуется три попытки подключения к серверу
        for _ in range(1, 4):
            try:
                logger.info(f'Открываем сокет и подключаемся к серверу '
                            f'{self.server_host}:{self.DEFAULT_PORT}')
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect((self.server_host, self.DEFAULT_PORT))
                    logger.info('Успешно подключились к серверу')
                    # Определяется размер данных для отправки на сервер и
                    # сколько байт необходимо для представления размера данных
                    data_size = len(data)
                    # Размер данных занимает минимальное необходимое
                    # количество байт (от 1 до 6)
                    size_bytes = data_size.to_bytes(next((
                        i for i in range(1, 7) if data_size < (1 << (i * 8))),
                        6), byteorder='big', signed=False)
                    logger.info(f'Размер данных: {len(size_bytes)} байт')
                    # Отправляются данные в формате <размер><данные>
                    s.sendall(size_bytes)
                    s.sendall(data)
                    sent_data = len(data) + len(size_bytes)
                    logger.info(f'Отправлено {sent_data} байт данных '
                                f'на сервер {self.server_host}')
                    return sent_data
            except ConnectionError as e:
                logger.error(f'Не удалось установить соединение из-за ошибки '
                             f'{e} сервера {self.server_host}. Повторное '
                             f'соединение через {self.RETRY_PERIOD} секунд.')
                time.sleep(self.RETRY_PERIOD)
        logger.error(f'Не удалось установить соединение с сервером '
                     f'{self.server_host} после трёх попыток')
        raise ConnectionError(f'Не удалось установить соединение с сервером '
                              f'{self.server_host} после трёх попыток')


class MyListener:
    ''' Принимает реквизиты сервера для запуска сервиса приёма данных.'''

    FIXED_BYTE_SIZE = 4  # фиксированный размер данных в байтах в протоколе
    INITIAL_BYTES_LEN = 16  # количество первых байт данных для вывода

    def __init__(self, service_ip, service_port) -> None:
        self.service_ip = service_ip
        self.service_port = service_port

    def start_tcp_service(self) -> None:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((self.service_ip, self.service_port))
                s.listen(1)
                logger.info(f'Сервис запущен на '
                            f'{self.service_ip}:{self.service_port}')
                while True:
                    conn, addr = s.accept()
                    with conn:
                        logger.info(f'Установлено подключение к {addr}')
                        self._receive_data(conn)
        except socket.error as e:
            logger.error(f'Ошибка при запуске сервера: {e}')
        except KeyboardInterrupt:
            logger.info('Сервер остановлен пользователем')

    def _receive_data(self, conn) -> None:
        try:
            # Получаем размер данных, отправленных клиентом
            size_bytes = conn.recv(self.FIXED_BYTE_SIZE)
            if not size_bytes:
                logger.info('Соединение закрыто клиентом')
                return
            size = int.from_bytes(size_bytes, byteorder='big', signed=False)
            # Получаем сами данные
            data = conn.recv(size)
            logger.info(f'Размер данных: {size}')
            logger.info(f'Первые {self.INITIAL_BYTES_LEN} байт данных в'
                        f'hex-формате: {data[:self.INITIAL_BYTES_LEN].hex()}')
        except socket.error as e:
            logger.error(f'Ошибка при получении данных: {e}')
        except struct.error as e:
            logger.error(f'Ошибка при распаковке данных: {e}')
        except Exception as e:
            logger.error(f'Неизвестная ошибка: {e}')


def main():
    try:
        role = sys.argv[1]
        if role == 'sender':
            server_host = sys.argv[2]
            sender = MySender(server_host)
            logger.info('Отправитель запущен')
            sender.create_tcp_connection()
        elif role == 'listener':
            service_ip = sys.argv[2]
            service_port = int(sys.argv[3])
            listener = MyListener(service_ip, service_port)
            logger.info(f'Сервер {service_ip} запущен. '
                        f'Прослушивание порта {service_port}')
            listener.start_tcp_service()
        else:
            print('Неверно указана роль. Допустимые роли: sender, listener')
    except IndexError:
        print('Использование: python main.py <role> <server_name_or_ip>'
              '[<host> <port>]')
    except Exception as e:
        logger.error(f'Произошла ошибка: {e}')
        logger.exception(e)


if __name__ == '__main__':
    main()

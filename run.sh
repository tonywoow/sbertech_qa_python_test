#!/bin/bash

# Получение списка IPv4-адресов
ILIST=$(ifconfig | grep 'inet ' | awk '{print $2}' | cut -d':' -f2)

# Установка номера порта
MIN_PORT=8080

COUNTER=0
for SERVER_IP in $ILIST; do
    # Запуск приложения в роли принимающей стороны
    LISTENER_PORT=$((MIN_PORT + COUNTER))
    LISTENER_LOG="listener_$COUNTER.log"
    python3 main.py listener "$SERVER_IP" "$LISTENER_PORT" > "$LISTENER_LOG" 2>&1 &
    LISTENER_PID=$!
    
    # Запуск приложения в роли отправителя
    SENDER_PORT=$LISTENER_PORT
    SENDER_LOG="sender_$COUNTER.log"
    python3 main.py sender "$SERVER_IP" > "$SENDER_LOG" 2>&1 &
    SENDER_PID=$!
    
    # Ожидание завершения отправки данных
    echo "Done. Press any key to exit."
    read -n1 -s
    
    # Завершение процессов приложений
    kill $LISTENER_PID
    echo "Killed listener process with PID $LISTENER_PID"
    kill $SENDER_PID
    echo "Killed sender process with PID $SENDER_PID"
    
    # Удаление временных файлов
    rm "$LISTENER_LOG" "$SENDER_LOG"
    
    # Увеличение счетчика
    COUNTER=$((COUNTER + 1))
done

#!/bin/bash
if [ ! -d ".venv" ]; then
    echo "Создаем виртуальное окружение..."
    python -m venv .venv
else
    echo "Виртуальное окружение уже существует."
fi

echo "Активируем виртуальное окружение..."
source .venv/Scripts/activate


if [ -f "requirements.txt" ]; then
    echo "Устанавливаем зависимости из requirements.txt..."
    pip install -r requirements.txt
else
    echo "Файл requirements.txt не найден."
fi

echo "Развертывание виртуального окружения завершено."
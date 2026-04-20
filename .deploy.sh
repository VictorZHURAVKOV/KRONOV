#!/bin/sh
# Одноразовый скрипт для установки SSH-ключа для deployment.
# После установки ключа Claude закончит deployment и этот файл можно удалить.
mkdir -p ~/.ssh
chmod 700 ~/.ssh
grep -q 'kronov-deploy@claude-code' ~/.ssh/authorized_keys 2>/dev/null || \
  echo 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIBvDw4TgeWhebLFrs9Seberz0Gmpxtvuga7h6qUetBWU kronov-deploy@claude-code' >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
echo READY

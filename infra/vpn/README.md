# VLESS Reality client (Xray) for VPS
#
# Назначение: на сервере в РФ (или где Telegram режется) поднять локальный
# SOCKS5/HTTP через VLESS+Reality. Worker/API ходят в Telegram через TELEGRAM_PROXY.
#
# Сейчас (за границей) VPN не нужен — TELEGRAM_PROXY оставь пустым.
#
# 1. Скопируй конфиг и заполни плейсхолдеры от своего VPN-провайдера / своего VLESS:
#      cp infra/vpn/xray.config.example.json infra/vpn/xray.config.json
#
# 2. Плейсхолдеры:
#      VPN_SERVER_HOST  — IP или домен VLESS-сервера
#      VPN_UUID         — UUID клиента
#      VPN_SNI_DOMAIN   — serverName / SNI (часто microsoft.com / google.com / свой)
#      VPN_PUBLIC_KEY   — Reality public key
#      VPN_SHORT_ID     — Reality shortId (может быть пустой строкой "")
#      port / flow      — как в твоей ссылке vless://...
#
# 3. Запуск вместе со стеком:
#      docker compose --profile vpn up -d xray
#
# 4. В .env на VPS:
#      TELEGRAM_PROXY=socks5://xray:1080
#    (внутри docker-сети имя сервиса `xray`)
#    Если worker не в docker:
#      TELEGRAM_PROXY=socks5://127.0.0.1:10808
#
# 5. xray.config.json в git не коммитить (секреты).

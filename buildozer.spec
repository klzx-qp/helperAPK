[app]
title = ИИ Ассистент
package.name = aiassistant
package.domain = org.aiassistant
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 1.0

# 【Ключевой момент 1】Жёсткая фиксация Python 3.11.1
# Без фиксации p4a попытается собрать Python 3.14 и потерпит неудачу.
# 3.11.1 — это версия, проверенная на совместимость с pyjnius и kivy [citation:5].
# hostpython3 и python3 должны быть согласованы.
requirements = python3==3.11.1, hostpython3==3.11.1, kivy, pyjnius, requests, urllib3, charset-normalizer, idna, certifi

orientation = portrait
fullscreen = 0

# 【Ключевой момент 2】Разрешения
# Оставлены только самые необходимые. Поскольку вы ранее изменили DATA_DIR на приватный каталог,
# READ/WRITE_EXTERNAL_STORAGE не нужны.
android.permissions = INTERNET, RECORD_AUDIO

# 【Ключевой момент 3】Версии Android
android.api = 33
android.minapi = 21
android.ndk = 25b
android.sdk = 33
android.accept_sdk_license = True
android.arch = arm64-v8a

[buildozer]
log_level = 2
warn_on_root = 1

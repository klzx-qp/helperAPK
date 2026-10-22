[app]
title = ИИ Ассистент
package.name = aiassistant
package.domain = org.aiassistant
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 1.0

requirements = python3,kivy,pyjnius,requests,urllib3,charset-normalizer,idna,certifi

orientation = portrait
fullscreen = 0

android.permissions = INTERNET,RECORD_AUDIO
android.api = 33
android.minapi = 21
android.ndk = 25b
android.sdk = 33
android.accept_sdk_license = True
android.arch = arm64-v8a
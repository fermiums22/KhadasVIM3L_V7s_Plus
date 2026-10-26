# Nika Robot / Khadas VIM3L

Виктор подтвердил маркировку **VIM3L** 26 октября 2026. Исходное задание называло
VIM3 ошибочно. Использовать только образ **vim3l**, не vim3.

## Фактический результат 26 октября 2026

Установлена и проверена **Ubuntu 24.04.5 LTS ARM64** на eMMC:
`/dev/mmcblk0p5`, тип носителя MMC, полный объём 14.6 GiB.
Имя `nika-robot-vim3l`, постоянный адрес Wi-Fi **192.168.0.125**.
Первоначальный проводной DHCP-адрес: 192.168.0.241.
ROS 2 Jazzy ROS Base установлен, четыре узла работают, `nika-robot.service`
активна и включена в автозапуск. После реальной перезагрузки boot_id изменился,
служба и восемь датчиков HA восстановились автоматически.

Устройство HA: [Nika Robot / Khadas VIM3L](http://192.168.0.4:8123/config/devices/device/9079c24914c66853815cad5d03d64ac1).

Проверены на реальной плате:

- чтение трёх ROS-топиков и обнаружение всех четырёх узлов;
- переход ROS в degraded при остановке heartbeat и восстановление running;
- все восемь датчиков HA переходят в unavailable при блокировке MQTT;
- автоматическое восстановление MQTT после снятия блокировки;
- перезагрузка платы, автозапуск ROS и возвращение телеметрии в HA;
- MQTT разрешает собственный topic (PUBACK 0x10) и запрещает чужой (0x87);
- после перезагрузки NRestarts=0, предупреждений/ошибок службы нет,
  временных firewall-правил не осталось.

Полное свидетельство: `acceptance-2026-10-26.json`, итоговый аудит:
`final-audit-2026-10-26.txt`. На последней проверке служба занимала около 229 MiB RAM,
свободно 11 GiB диска. Это разовые замеры.

Штатный reboot проверен; физическое снятие питания и работа с моторами/камерами
не проверялись. Для независимости от компьютера нужно отдельное питание USB-C;
работа служб от Windows не зависит.

## Доступ и обслуживание

Заводской пароль khadas заменён, SSH-пароли отключены; вход проверен по отдельному ключу.
Локальный ключ: `D:/HAOS/ssh/khadas_vim3l_ed25519`, закреплённый ключ хоста:
`D:/HAOS/ssh/khadas_vim3l_known_hosts`.
Пароль для sudo сохранён отдельно в `D:/HAOS/ssh/khadas_vim3l_password.txt`
с ограниченными Windows ACL; значение не помещается в исходники и журнал.

```powershell
ssh -i D:/HAOS/ssh/khadas_vim3l_ed25519 -o UserKnownHostsFile=D:/HAOS/ssh/khadas_vim3l_known_hosts khadas@192.168.0.125
```

На плате: исходники `/opt/nika-robot/ros_ws/src/nika_robot`, служба `nika-robot`,
настройки `/etc/nika-robot/robot.env`, пароль MQTT `/etc/nika-robot/mqtt-password`.
Аккаунт брокера `nika-khadas-vim3l` ограничен своими topics.
Существующие права остальных MQTT-пользователей сохранены. Резерв брокера:
`CT103:/root/config-backups/nika-khadas-20261026-151732`.
Сеть Ethernet подключается автоматически, системные таймеры обновлений включены,
часовой пояс Europe/Minsk. Wi-Fi DHCP закреплён на роутере Archer C6:
`18-93-7F-67-78-4A → 192.168.0.125`.

## Wi-Fi и панель HA

Основной профиль NetworkManager `nika-home-5g`: `Fermiums`, 5 ГГц,
автоподключение, приоритет 100. Резервный `nika-home-24g`: `Fermiums_2.4`,
2.4 ГГц, приоритет 50. У обоих постоянный аппаратный MAC и метрика маршрута 50.
Пароли находятся только на плате в root-only профилях NetworkManager.
`tools/setup_wifi_from_windows.py` переносит сохранённые Windows WLAN-профили
по SSH, не выводя пароли. Для первоначального подключения через кабель можно
переопределить `KHADAS_SSH_TARGET=khadas@192.168.0.241`.

После реального reboot 26.10.2026 изменился boot_id, автоматически восстановились
Fermiums (5180 МГц), IP .125, служба ROS и все восемь сущностей HA.
При отключённом через NetworkManager eth0 MQTT и SSH проверены через wlan0.
Переключение на резервную сеть 2.4 ГГц отдельно не проверялось.

Панель [Робот](http://192.168.0.4:8123/nika-robot/overview) находится в боковом меню HA.
Исходник: `home-assistant/robot-dashboard.json`; публикация:
`python tools/deploy_dashboard.py`. Скрипт сохраняет резервную копию существующей
панели, проверяет сущности и сравнивает результат чтения с отправленным конфигом.
STM32, движение и одометрия отображаются как ещё не подключённые.

На рабочем столе владельца создан единственный профиль `Khadas_VIM3L.tlp`:
khadas@192.168.0.125:22, ключ клиента и ключи хоста сохранены внутри профиля.
Вход проверен через Bitvise sexec с `-noRegistry`; профиль не хранится в Git.

Проверку ROS запускать от пользователя службы: Fast DDS shared-memory permissions
разделяют пользователей `khadas` и `nika-robot`.

```bash
sudo -u nika-robot bash /opt/nika-robot/verify.sh
systemctl status nika-robot
journalctl -u nika-robot -b
```

При первичной сборке исправлен некорректный maintainer email в package.xml.
Установщик теперь проверяет ROS-манифест перед сборкой, чтобы colcon не принимал
пакет молча за обычный Python-проект.

## Подготовлено

- `tools/download_official.py`: загрузка с dl.khadas.com через CT103 и проверенный
  прямой маршрут `192.168.0.1 dev eth0`, без proxy и изменения маршрутов.
- Ubuntu Server 24.04 ARM64, Fenix 1.7.5, Linux 5.15, eMMC image.
- ROS Jazzy package `ros_ws/src/nika_robot`, четыре отдельных процесса.
- `install.sh`, `start.sh`, systemd unit и шаблон параметров MQTT.
- Тесты `python -m unittest discover -s tests -v` (из D:/HAOS).

Образ VIM3 скачан до уточнения модели и **не должен прошиваться**.
Контрольные SHA256 в downloads фиксируют локальную целостность загрузки;
это не подписанные производителем контрольные суммы. Проверять архив через 7-Zip.
Python lzma на этой Windows сообщил EOF на VIM3-архиве с нулевым padding,
но 7-Zip проверил все блоки и CRC64 успешно. Для прошивки нужен распакованный .img.

## Архитектура и ограничения

Сервер Ники сохраняет LLM, память, голос и автономную логику.
Khadas публикует телеметрию в существующий MQTT `192.168.0.8:1883`.
Адрес и наличие учётных данных проверены чтением конфигурации HA;
TCP и активность Mosquitto проверены. Пароли в исходниках отсутствуют.

- `diagnostics`: реальные /proc и /sys, корневой диск; отсутствие температуры даёт unknown.
- `server_bridge`: MQTT discovery, LWT, переподключение, повторная discovery после
  перезапуска HA; данные без retain, срок годности 30 секунд.
- `motion`: только статус disabled_no_hardware; нет подписки cmd_vel и доступа к UART/GPIO.
- `odometry`: unavailable_no_encoders; не публикует ложные /odom и TF.

Состояние ROS running означает получение свежих сообщений всех трёх узлов мостом,
а не готовность робота ездить. Через 15 секунд без сообщений состояние degraded,
устаревшие метрики исключаются. STM32 обозначен not_connected до реализации транспорта.
Systemd закрывает доступ к физическим устройствам, DDS ограничен localhost.
Мост не принимает исполнительных команд из MQTT. Интеграция исполнительных действий
Ники — следующий этап с отдельным проверенным протоколом, а не произвольный shell.

## Существующий протокол робота

Изучены локальные рабочие копии реальных GitHub-проектов:

| Проект | HEAD | Роль |
|---|---|---|
| V7s_Plus | b1c29e1cf53abc0396fd09a6fdc9e4cc479e85db | STM32F071, силовая часть |
| ESP32S3_V7s_Plus | 9f48fd8f577afb7d23d4607fd8f9e466f2f28b49 | Главный контроллер и ESPHome |
| ESP32_V7s_Plus | 2e1abe121cfe9221cfac9413ee29a754dce483e8 | Отдельный GoPro bridge |

Рабочие файлы могут отличаться от HEAD; прошивки не изменялись.
`ESP32S3_V7s_Plus/v7s-plus.yaml`: STM32 address 1, UART 921600 8N1,
S3 GPIO42 TX → STM32 RX, GPIO41 RX ← STM32 TX.
Отдельный UART S3 GPIO17/18: ESP32 bridge address 2, 115200 8N1.
`V7s_Plus/Core/Src/modbus_slave.c`: версия протокола в 0x0000 = 6;
левый энкодер high/low 0x0062/63, правый 0x006A/6B; скорости в десятых RPM
0x0061/69; зарядка 0x00B0–0x00B8 (status/state/fault/duty/Vbat/Ibat/Vin/sequence/auto).

Khadas добавляется поверх ESP32-S3 по сети. Второй TX на существующий UART запрещён.
Будущая одометрия требует атомарных пар high/low, знака и переполнения счётчика,
реальных timestamp, направления, калибровки edges/revolution и геометрии.
Один только GPIO/Modbus online не подтверждает безопасность движения.

## Установка на Windows и плату

1. VIM3L подключить USB-кабелем с данными. Три нажатия Function за 2 секунды
   включают Upgrade Mode. Windows должна видеть WorldCup Device.
2. USB Burning Tool уже установлен: `C:/Program Files (x86)/Amlogic/USB_Burning_Tool/`.
   Импортировать **vim3l-ubuntu-24.04-server-linux-5.15-fenix-1.7.5-250925-emmc.img**.
   Запись уничтожает прежний HAOS на этой плате. Не трогать домашний HA `192.168.0.4`.
3. Дождаться успешной записи/проверки, затем загрузить плату и подключить Ethernet
   к домашней сети. Если Ethernet отсутствует — настроить Wi-Fi на самой плате.
4. Подтвердить `/proc/device-tree/model`, Ubuntu 24.04, `aarch64`, наличие eMMC,
   корневой filesystem на eMMC и отсутствие зависимости от microSD.
5. Настроить SSH с ключом владельца и сменить заводской пароль, проверить повторный вход.
6. Скопировать этот каталог **без downloads** на плату, запустить `sudo bash install.sh`.
   Скрипт проверяет модель/ОС, ставит ROS Base, обновления, SSH и systemd unit.
7. Создать отдельную MQTT-учётную запись с правами публикации своих state/availability
   и discovery, подписки только на homeassistant/status. Не помещать пароль в git/команды.
   Скопировать robot.env.example в `/etc/nika-robot/robot.env`, указать пользователя.
   Пароль в `/etc/nika-robot/mqtt-password`, владелец root:nika-robot, режим 0640;
   файл robot.env также root:nika-robot 0640. Затем `systemctl start nika-robot`.

## Повторная приёмка на реальном устройстве

Проверить systemctl status nika-robot и journalctl; четыре узла ROS; device в HA;
сверить температуру/память/диск с ОС; отключить Ethernet и проверить unavailable;
восстановить сеть и проверить recovery; перезапустить один узел и проверить degraded;
перезагрузить плату и проверить автозапуск с новым boot_id.
Физическое отключение питания проверяется владельцем после штатного shutdown.
Локальные тесты и ранняя проверка сборщика метрик на CT103 сами по себе не доказывают
работу на Khadas; итоговые проверки на реальной плате перечислены выше.

## Официальные источники

- https://dl.khadas.com/products/vim3l/firmware/ubuntu/emmc/ubuntu-24.04/
- https://docs.khadas.com/products/sbc/vim3/install-os/install-os-into-emmc-via-usb-tool
- https://docs.khadas.com/products/sbc/vim3/install-os/boot-into-upgrade-mode
- https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html
- https://github.com/ros2/ros2_documentation/blob/jazzy/source/Installation/_Apt-Repositories.rst
- https://www.home-assistant.io/integrations/mqtt/

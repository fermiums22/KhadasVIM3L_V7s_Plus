# Khadas VIM3L — вычислительный узел робота V7s Plus / Ника

Ubuntu Server 24.04 ARM64 на eMMC, ROS 2 Jazzy, диагностика и MQTT → Home Assistant.
Сервер Ники выполняет LLM, память и голосовую логику; VIM3L — бортовой Linux-узел.

**Текущий комплект:** STM32F071 + I²S-микрофон с выводами WS/SCK/SD/VDD/GND/L/R
+ модуль **PCM5102/PCM5102A** с линейным выходом. TPA2016D2 исключён из этой схемы
по решению Виктора. Точная модель микросхемы микрофона по присланному фото не установлена.

## ASCII-колодка VIM3L и назначение контактов

Ниже **физические номера контактов**, не Linux GPIO numbers. У Khadas два ряда
**1…20 и 21…40**, а не нечётный/чётный ряд Raspberry Pi. Рисунок условно повёрнут
контактами 1/21 вверх. Перед пайкой найти метку **1** на своей плате и сверить
ориентацию по [официальной схеме/шелкографии своей ревизии](https://dl.khadas.com/products/vim3l/schematics/).
Вид со стороны пайки будет зеркальным. MCU_NRST на pin 7 относится к MCU самой VIM!

```text
                  KHADAS VIM3L — 40-PIN HEADER
                РЯД 1..20              РЯД 21..40
           +----------------+-----------------------------+
  5V (*)   | 01 [o]         |         [o] 21 | GND         |
  5V       | 02 [o]         |         [o] 22 | I2C3 SCL    | spare
  USB DM   | 03 [o]         |         [o] 23 | I2C3 SDA    | spare
  USB DP   | 04 [o]         |         [o] 24 | GND         |
  GND      | 05 [o]         |         [o] 25 | I2C AO SCL  | reserved
  MCU 3V3  | 06 [o]         |         [o] 26 | I2C AO SDA  | reserved
  MCU NRST | 07 [o]         |         [o] 27 | 3V3 (**)    |
  MCU SWIM | 08 [o]         |         [o] 28 | GND AUDIO   | --> MIC/DAC GND
  GND      | 09 [o]         |         [o] 29 | I2S BCLK    | --> MIC SCK + DAC BCK
  ADC0     | 10 [o]         |         [o] 30 | I2S MCLK    | unused in 3-wire mode
  1V8      | 11 [o]         |         [o] 31 | I2S DOUT    | --> DAC DIN
  ADC1     | 12 [o]         |         [o] 32 | I2S LRCLK   | --> MIC WS + DAC LCK
  SPDIF    | 13 [o]         |         [o] 33 | I2S DIN     | <-- MIC SD
  GND      | 14 [o]         |         [o] 34 | GND         |
  UARTC RX | 15 [o]         |         [o] 35 | GPIOH_5     | spare / PWM_F
  UARTC TX | 16 [o]         |         [o] 36 | RTC CLK     | reserved
  GND      | 17 [o]         |         [o] 37 | GPIOH_4     | --> STM BOOT0 (1k)
  DEBUG RX | 18 [o]         |         [o] 38 | MCU PA1     | reserved
  DEBUG TX | 19 [o]         |         [o] 39 | GPIOZ_15    | --> RESET transistor
  3V3      | 20 [o]         |         [o] 40 | GND STM32   | --> STM GND
           +----------------+-----------------------------+

  pin 15 (VIM RX) <--- STM32 PA9  / USART1 TX
  pin 16 (VIM TX) ---> STM32 PA10 / USART1 RX
  pin 20 (3V3)   ---> MIC VDD     [only for a confirmed 3.3-V module]

  (*)  pin 01 -> DAC VIN/VCC ONLY if the module's regulated input accepts 5 V.
  (**) pin 27 -> DAC 3V3 ONLY if it is a documented direct 3.3-V supply input.
       Choose ONE supply path. Never connect 5 V to the chip's 3V3 rail.
```

Расположение и альтернативные функции сверены с
[Khadas 40-pin header](https://docs.khadas.com/products/sbc/vim3/applications/gpio/40pin-header).
Не переносить абсолютные GPIO-номера из таблиц Linux 4.9/5.15: на установленной
VIM3L базы gpiochip отличаются. Использовать имена линий и актуальный pinctrl.

## STM32: UART, BOOT0 и RESET

| Сигнал | VIM3L | STM32 / включение |
|---|---|---|
| Приём VIM | **15**, GPIOH_6 / UART_C RX | PA9 / USART1 TX |
| Передача VIM | **16**, GPIOH_7 / UART_C TX | PA10 / USART1 RX |
| BOOT0 | **37**, GPIOH_4 | Через 1 кОм на BOOT0; около 10 кОм от BOOT0 к GND |
| RESET control | **39**, GPIOZ_15 | На затвор N-MOS через 1 кОм; сток к NRST, исток к GND |
| Общая земля | **40** или **17** | GND платы STM32 |

Все UART/GPIO — логика **3.3 В**, не RS-232. STM32 питается от собственной платы:
силовое питание робота через VIM не подавать. GPIO соединять при согласованном питании,
чтобы не запитывать выключенную плату через сигнальные выводы.

```text
VIM pin 37 -- 1k --+---------------- STM BOOT0
                  |
                 10k                normal boot: BOOT0 = 0
                  |                 ROM boot:    BOOT0 = 1 during reset
                 GND

VIM pin 39 -- 1k --+-- G   N-MOS, suitable for 3.3-V gate drive
                  |       D -------- STM NRST
                100k      S -------- GND
                  |
                 GND

STM NRST retains its pull-up to STM32's own 3V3.
GPIO39 = 1 -> transistor ON  -> NRST = 0 (reset)
GPIO39 = 0 -> transistor OFF -> NRST released
```

Не соединять NRST с push-pull выходом, который активно подаёт высокий уровень.
Не путать **pin 7 MCU_NRST VIM** с RESET внешней STM32. Подтяжка затвора удерживает
reset-транзистор закрытым, пока GPIO VIM не настроен.

**Сейчас эти же UART/BOOT0/NRST обслуживает ESP32-S3.** Перед прямым подключением
VIM физически отключить соответствующие выходы S3 либо установить согласованный
переключатель/мультиплексор. Просто выключить питание S3 недостаточно. Два TX,
а также два управляющих выхода BOOT0 на одну линию не подключать.

Рабочий протокол STM32: Modbus RTU, address **1**, **921600 8N1**. ROM-загрузчик
имеет другой режим UART (ST USART boot protocol, обычно 8E1); параметры рабочего
приложения нельзя автоматически использовать для прошивки. Текущий ROS-код **не
открывает UART и не переключает BOOT/RESET**. Включение прямого управления — отдельный
этап после переключения владельца интерфейса. Связь ESP32-S3→STM32 сейчас не изменена.

## I²S-микрофон с фотографии

| Микрофон | Подключение | Направление относительно VIM |
|---|---|---|
| **WS** | **32** — GPIOA_2, LRCLK | Выход VIM → вход микрофона |
| **SCK** | **29** — GPIOA_1, BCLK | Выход VIM → вход микрофона |
| **SD** | **33** — GPIOA_4, I2S DIN | Выход микрофона → вход VIM |
| **VDD** | **20**, 3.3 В, после подтверждения питания модуля | Питание |
| **GND** | **28** | Общая земля |
| **L/R** | Локально к GND для левого канала, если модуль использует стандартную полярность INMP441 | На колодку выводить не нужно |

У INMP441 L/R=GND выбирает левый слот, L/R=VDD — правый. Для неопознанной
микросхемы это условная схема: до пайки подтвердить модель, допустимое VDD и полярность
L/R. **Не оставлять L/R плавающим и не подавать 5 В на VDD микрофона.**
Pin 31 — выход VIM, подключать к нему SD микрофона нельзя.
Если это INMP441, проверить также наличие на модуле развязки 0.1 мкФ у VDD,
подтяжки SD 100 кОм к земле и подключения CHIPEN к VDD:
[даташит TDK, таблица выводов](https://invensense.tdk.com/wp-content/uploads/2015/02/INMP441.pdf).

## PCM5102: I²S-ЦАП и линейный выход

| PCM5102-модуль | Подключение |
|---|---|
| **BCK** | **29**, вместе с SCK микрофона |
| **LCK / LRCK / WS** | **32**, вместе с WS микрофона |
| **DIN** | **31**, GPIOA_3 / I2S DOUT |
| **GND** | **28** или **34** |
| **SCK** | К GND локально на модуле в режиме 3-wire / BCK PLL |
| **VIN / VCC** | **01 (5 В)** только для подтверждённого входа модуля со стабилизатором 5→3.3 В |
| Отдельный **3V3** | Альтернатива: **27 (3.3 В)** только если документация модуля допускает питание через этот вывод |

**SCK микрофона = BCLK. SCK PCM5102 = MCLK. Это разные сигналы.**
Для выбранного трёхпроводного режима DAC SCK удерживается в нуле, а pin 30 VIM
остаётся неподключённым. Питание конкретной платы GY-PCM5102 по рекламному фото
не подтверждено: различать вход VIN, шину 3V3 и выход стабилизатора; не подключать оба
варианта питания одновременно.

На самом PCM5102A аппаратные уровни: FMT=0 — I²S, XSMT=1 — снятие mute,
DEMP=0 — без de-emphasis. Эти уровни обычно задаются перемычками модуля;
позиции H1/H2/H3/H4 не переносить между разными платами без их схемы.
I²C/SDA/SCL и SHDN от TPA2016 здесь больше не нужны.

```text
                       +---------------- I2S MIC
VIM 29  BCLK ----------+--> SCK
                       +---------------- PCM5102 BCK

                       +---------------- I2S MIC WS
VIM 32  LRCLK ---------+---------------- PCM5102 LCK/LRCK

VIM 33  DIN  <-------------------------- I2S MIC SD
VIM 31  DOUT --------------------------> PCM5102 DIN
                                         PCM5102 SCK --- GND

PCM5102 LINE OUT / jack ---> active speaker / amplifier LINE IN
```

PCM5102 — **не усилитель мощности**. Обычный динамик 4/8 Ом и низкоомные наушники
к линейному выходу напрямую не подключать. Для пассивного динамика всё равно понадобится
усилитель. Режим без MCLK и электрические параметры описаны в
[TI PCM5102A datasheet](https://www.ti.com/lit/ds/symlink/pcm5102a.pdf), разделы 7–9.

## Что уже работает, а что только спланировано

Проверено: Ubuntu на eMMC, SSH по ключу, ROS Jazzy, MQTT discovery, восемь датчиков
HA, обнаружение устаревших сообщений, восстановление после потери MQTT и reboot.
Отчёт: [acceptance-2026-10-26.json](acceptance-2026-10-26.json).

**Электрическая разводка выше — план подключения, не отчёт об аппаратном тесте.**
На плате сейчас GPIO37/39 свободны, UART_C и I²S на колодке не активированы.
I²C3 уже включён по умолчанию, но для PCM5102 не нужен.

На установленном Linux 5.15 файл конфигурации:
`/boot/dtb/amlogic/kvim3l.dtb.overlay.env`. Текущая строка: `fdt_overlays=`.
Overlay `uart3.dtbo` существует. Штатный `i2s.dtbo` подключает `tdmb_mclk`,
`tdmout_b`, `tdm_b_clk_pins`, **но не `tdmin_b`**. Поэтому одного `i2s` для микрофона
недостаточно: понадобятся pinctrl `tdmin_b` и проверка capture-маршрута ALSA.
Это установлено чтением реального DT, не догадкой по схеме. Общие BCLK/WS требуют
согласованных частоты дискретизации и размера слотов у playback и capture.

Скрипт [tools/inspect_hardware.sh](tools/inspect_hardware.sh) только читает конфигурацию;
снимок — [docs/hardware-inspection-2026-10-26.txt](docs/hardware-inspection-2026-10-26.txt).
Драйверы микрофона/DAC, переключение UART на VIM и управление GPIO в этой задаче
не включались. Служба диагностики остаётся без доступа к физическим устройствам.

## Исходники, установка и обслуживание

| Путь | Назначение |
|---|---|
| `ros_ws/src/nika_robot/` | Узлы diagnostics, server_bridge, motion, odometry |
| `install.sh`, `start.sh`, `verify.sh` | Установка ROS, запуск и диагностика |
| `systemd/`, `config/` | Unit и шаблон настроек MQTT |
| `tools/` | Загрузка официального образа, SSH/HA-проверки, приёмка |
| `tests/` | Проверки телеметрии и устаревания данных |
| `docs/DEPLOYMENT.md` | Реальный развёрнутый узел, доступ, установка, протокол робота |

```powershell
# Из корня этого репозитория:
python -m unittest discover -s tests -v
```

Полная инструкция: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).
Рабочий адрес VIM3L: `192.168.0.241` (DHCP), имя `nika-robot-vim3l`.
Секреты и SSH-ключи остаются вне репозитория в `D:/HAOS/ssh/`.
Большие образы и USB Burning Tool — локальные артефакты `downloads/`, исключены из Git.

Официальные источники: [Khadas UART](https://docs.khadas.com/products/sbc/vim3/applications/gpio/uart),
[Khadas I²S](https://docs.khadas.com/products/sbc/vim3/applications/gpio/i2s),
[Khadas I²C](https://docs.khadas.com/products/sbc/vim3/applications/gpio/i2c).
STM32: [V7s_Plus](https://github.com/fermiums22/V7s_Plus),
[ESP32S3_V7s_Plus](https://github.com/fermiums22/ESP32S3_V7s_Plus).

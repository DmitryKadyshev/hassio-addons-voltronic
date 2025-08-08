#!/usr/bin/env bashio
# set +u
# echo "Start"
# printenv
# bashio::log.info "Доступные параметры: $(bashio::config)"

# set -euo pipefail

declare DEVICE
declare RUN_INTERVAL
declare AMPERAGE_FACTOR
declare WATT_FACTOR
declare QPIRI
declare QPIWS
declare QMOD
declare QPIGS
declare MQTT_SERVER
declare MQTT_PORT
declare MQTT_TOPIC
declare DEVICENAME
declare MQTT_USERNAME
declare MQTT_PASSWORD

# === Пути к конфигурационным файлам ===
INVERTER_CONF="/opt/inverter-cli/inverter.conf"


# === Чтение настроек из конфигурации аддона ===
DEVICE=$(bashio::config 'device')
RUN_INTERVAL=$(bashio::config 'run_interval')
AMPERAGE_FACTOR=$(bashio::config 'amperage_factor')
WATT_FACTOR=$(bashio::config 'watt_factor')
QPIRI=$(bashio::config 'qpiri')
QPIWS=$(bashio::config 'qpiws')
QMOD=$(bashio::config 'qmod')
QPIGS=$(bashio::config 'qpigs')

MQTT_SERVER=$(bashio::config 'mqtt_server')
MQTT_PORT=$(bashio::config 'mqtt_port')
MQTT_TOPIC=$(bashio::config 'mqtt_topic')
DEVICENAME=$(bashio::config 'devicename')
MQTT_USERNAME=$(bashio::config 'mqtt_username')
MQTT_PASSWORD=$(bashio::config 'mqtt_password')

# === Генерация inverter.conf ===
cat > "$INVERTER_CONF" << EOF
device=$DEVICE
run_interval=$RUN_INTERVAL
amperage_factor=$AMPERAGE_FACTOR
watt_factor=$WATT_FACTOR
qpiri=$QPIRI
qpiws=$QPIWS
qmod=$QMOD
qpigs=$QPIGS
EOF

bashio::log.info "Конфиг inverter.conf создан: $INVERTER_CONF"

cat $INVERTER_CONF

bashio::log.info "Проверка доступности mosquitto_pub..."
if ! command -v mosquitto_pub >/dev/null 2>&1; then
    bashio::log.fatal "mosquitto_pub не установлен. Установите пакет mosquitto-clients" 
fi

bashio::log.info "Проверка подключения к MQTT... -h $MQTT_SERVER -p $MQTT_PORT -u $MQTT_USERNAME -P $MQTT_PASSWORD"
if ! echo "test" | mosquitto_pub -h "$MQTT_SERVER" -p "$MQTT_PORT" -u "$MQTT_USERNAME" -P "$MQTT_PASSWORD" -t "homeassistant/test" -s; then
    bashio::log.warning "Не удалось подключиться к MQTT. Проверьте сервер, порт и учётные данные."
else
    bashio::log.info "Подключение к MQTT успешно."
fi

# === Функция: регистрация MQTT-сенсоров (аналог mqtt-init.sh) ===
mqtt_init() {
    bashio::log.info "Регистрация MQTT-сенсоров (аналог mqtt-init.sh)..."

    registerTopic() {
        local key="$1"
        local unit="$2"
        local icon="$3"
        local topic="$MQTT_TOPIC/sensor/${DEVICENAME}_${key}/config"
        local payload="{
            \"name\": \"${DEVICENAME}_${key}\",
            \"unit_of_measurement\": \"$unit\",
            \"state_topic\": \"$MQTT_TOPIC/sensor/${DEVICENAME}_${key}\",
            \"icon\": \"mdi:$icon\"
        }"

        mosquitto_pub \
            --quiet \
            -h "$MQTT_SERVER" \
            -p "$MQTT_PORT" \
            -u "$MQTT_USERNAME" \
            -P "$MQTT_PASSWORD" \
            -t "$topic" \
            -m "$payload" || bashio::log.warning "Ошибка регистрации сенсора: $key"
    }

    registerInverterRawCMD() {
        local topic="$MQTT_TOPIC/sensor/${DEVICENAME}/config"
        local payload="{
            \"name\": \"${DEVICENAME}\",
            \"state_topic\": \"$MQTT_TOPIC/sensor/${DEVICENAME}\"
        }"

        mosquitto_pub \
            --quiet \
            -h "$MQTT_SERVER" \
            -p "$MQTT_PORT" \
            -u "$MQTT_USERNAME" \
            -P "$MQTT_PASSWORD" \
            -t "$topic" \
            -m "$payload" || bashio::log.warning "Ошибка регистрации сырого сенсора"
    }

    # Регистрация всех сенсоров
    registerTopic "Inverter_mode" "" "solar-power"
    registerTopic "AC_grid_voltage" "V" "power-plug"
    registerTopic "AC_grid_frequency" "Hz" "current-ac"
    registerTopic "AC_out_voltage" "V" "power-plug"
    registerTopic "AC_out_frequency" "Hz" "current-ac"
    registerTopic "PV_in_voltage" "V" "solar-panel-large"
    registerTopic "PV_in_current" "A" "solar-panel-large"
    registerTopic "PV_in_watts" "W" "solar-panel-large"
    registerTopic "PV_in_watthour" "Wh" "solar-panel-large"
    registerTopic "SCC_voltage" "V" "current-dc"
    registerTopic "Load_pct" "%" "brightness-percent"
    registerTopic "Load_watt" "W" "chart-bell-curve"
    registerTopic "Load_watthour" "Wh" "chart-bell-curve"
    registerTopic "Load_va" "VA" "chart-bell-curve"
    registerTopic "Bus_voltage" "V" "details"
    registerTopic "Heatsink_temperature" "" "details"
    registerTopic "Battery_capacity" "%" "battery-outline"
    registerTopic "Battery_voltage" "V" "battery-outline"
    registerTopic "Battery_charge_current" "A" "current-dc"
    registerTopic "Battery_discharge_current" "A" "current-dc"
    registerTopic "Load_status_on" "" "power"
    registerTopic "SCC_charge_on" "" "power"
    registerTopic "AC_charge_on" "" "power"
    registerTopic "Battery_recharge_voltage" "V" "current-dc"
    registerTopic "Battery_under_voltage" "V" "alert"
    registerTopic "Battery_bulk_voltage" "V" "current-dc"
    registerTopic "Battery_float_voltage" "V" "current-dc"
    registerTopic "Max_grid_charge_current" "A" "current-ac"
    registerTopic "Max_charge_current" "A" "current-ac"
    registerTopic "Out_source_priority" "" "grid"
    registerTopic "Charger_source_priority" "" "solar-power"
    registerTopic "Battery_redischarge_voltage" "V" "battery-negative"
    registerTopic "Warnings" "" "alert"

    # Регистрация сырого сенсора
    registerInverterRawCMD

    bashio::log.info "Регистрация MQTT-сенсоров завершена."
}

# === Функция: отправка данных (аналог mqtt-push.sh) ===
mqtt_push() {
    bashio::log.debug "Запуск mqtt_push..."

    # Опрос инвертора
    INVERTER_DATA=$(timeout 10 /opt/inverter-cli/bin/inverter_poller -1 2>/dev/null)
    if [ $? -ne 0 ] || [ -z "$INVERTER_DATA" ]; then
        bashio::log.warning "Не удалось получить данные от инвертора"
        return 1
    fi

    # Логирование
    TIME=$(date '+%Y.%m.%d-%H:%M:%S')
    echo "[$TIME] $INVERTER_DATA"

    # Функция отправки в MQTT
    pushMQTTData() {
        local key="$1"
        local value="$2"
        local topic="$MQTT_TOPIC/sensor/${DEVICENAME}_${key}"

        mosquitto_pub \
            --quiet \
            -h "$MQTT_SERVER" \
            -p "$MQTT_PORT" \
            -u "$MQTT_USERNAME" \
            -P "$MQTT_PASSWORD" \
            -t "$topic" \
            -m "$value" || bashio::log.warning "Ошибка публикации: $topic"
    }

    # Извлечение и отправка данных (точно как в оригинальном mqtt-push.sh)
    Inverter_mode=$(echo "$INVERTER_DATA" | jq -r '.Inverter_mode // empty')
    [ ! -z "$Inverter_mode" ] && pushMQTTData "Inverter_mode" "$Inverter_mode"

    AC_grid_voltage=$(echo "$INVERTER_DATA" | jq -r '.AC_grid_voltage // empty')
    [ ! -z "$AC_grid_voltage" ] && pushMQTTData "AC_grid_voltage" "$AC_grid_voltage"

    AC_grid_frequency=$(echo "$INVERTER_DATA" | jq -r '.AC_grid_frequency // empty')
    [ ! -z "$AC_grid_frequency" ] && pushMQTTData "AC_grid_frequency" "$AC_grid_frequency"

    AC_out_voltage=$(echo "$INVERTER_DATA" | jq -r '.AC_out_voltage // empty')
    [ ! -z "$AC_out_voltage" ] && pushMQTTData "AC_out_voltage" "$AC_out_voltage"

    AC_out_frequency=$(echo "$INVERTER_DATA" | jq -r '.AC_out_frequency // empty')
    [ ! -z "$AC_out_frequency" ] && pushMQTTData "AC_out_frequency" "$AC_out_frequency"

    PV_in_voltage=$(echo "$INVERTER_DATA" | jq -r '.PV_in_voltage // empty')
    [ ! -z "$PV_in_voltage" ] && pushMQTTData "PV_in_voltage" "$PV_in_voltage"

    PV_in_current=$(echo "$INVERTER_DATA" | jq -r '.PV_in_current // empty')
    [ ! -z "$PV_in_current" ] && pushMQTTData "PV_in_current" "$PV_in_current"

    PV_in_watts=$(echo "$INVERTER_DATA" | jq -r '.PV_in_watts // empty')
    [ ! -z "$PV_in_watts" ] && pushMQTTData "PV_in_watts" "$PV_in_watts"

    PV_in_watthour=$(echo "$INVERTER_DATA" | jq -r '.PV_in_watthour // empty')
    [ ! -z "$PV_in_watthour" ] && pushMQTTData "PV_in_watthour" "$PV_in_watthour"

    SCC_voltage=$(echo "$INVERTER_DATA" | jq -r '.SCC_voltage // empty')
    [ ! -z "$SCC_voltage" ] && pushMQTTData "SCC_voltage" "$SCC_voltage"

    Load_pct=$(echo "$INVERTER_DATA" | jq -r '.Load_pct // empty')
    [ ! -z "$Load_pct" ] && pushMQTTData "Load_pct" "$Load_pct"

    Load_watt=$(echo "$INVERTER_DATA" | jq -r '.Load_watt // empty')
    [ ! -z "$Load_watt" ] && pushMQTTData "Load_watt" "$Load_watt"

    Load_watthour=$(echo "$INVERTER_DATA" | jq -r '.Load_watthour // empty')
    [ ! -z "$Load_watthour" ] && pushMQTTData "Load_watthour" "$Load_watthour"

    Load_va=$(echo "$INVERTER_DATA" | jq -r '.Load_va // empty')
    [ ! -z "$Load_va" ] && pushMQTTData "Load_va" "$Load_va"

    Bus_voltage=$(echo "$INVERTER_DATA" | jq -r '.Bus_voltage // empty')
    [ ! -z "$Bus_voltage" ] && pushMQTTData "Bus_voltage" "$Bus_voltage"

    Heatsink_temperature=$(echo "$INVERTER_DATA" | jq -r '.Heatsink_temperature // empty')
    [ ! -z "$Heatsink_temperature" ] && pushMQTTData "Heatsink_temperature" "$Heatsink_temperature"

    Battery_capacity=$(echo "$INVERTER_DATA" | jq -r '.Battery_capacity // empty')
    [ ! -z "$Battery_capacity" ] && pushMQTTData "Battery_capacity" "$Battery_capacity"

    Battery_voltage=$(echo "$INVERTER_DATA" | jq -r '.Battery_voltage // empty')
    [ ! -z "$Battery_voltage" ] && pushMQTTData "Battery_voltage" "$Battery_voltage"

    Battery_charge_current=$(echo "$INVERTER_DATA" | jq -r '.Battery_charge_current // empty')
    [ ! -z "$Battery_charge_current" ] && pushMQTTData "Battery_charge_current" "$Battery_charge_current"

    Battery_discharge_current=$(echo "$INVERTER_DATA" | jq -r '.Battery_discharge_current // empty')
    [ ! -z "$Battery_discharge_current" ] && pushMQTTData "Battery_discharge_current" "$Battery_discharge_current"

    Load_status_on=$(echo "$INVERTER_DATA" | jq -r '.Load_status_on // empty')
    [ ! -z "$Load_status_on" ] && pushMQTTData "Load_status_on" "$Load_status_on"

    SCC_charge_on=$(echo "$INVERTER_DATA" | jq -r '.SCC_charge_on // empty')
    [ ! -z "$SCC_charge_on" ] && pushMQTTData "SCC_charge_on" "$SCC_charge_on"

    AC_charge_on=$(echo "$INVERTER_DATA" | jq -r '.AC_charge_on // empty')
    [ ! -z "$AC_charge_on" ] && pushMQTTData "AC_charge_on" "$AC_charge_on"

    Battery_recharge_voltage=$(echo "$INVERTER_DATA" | jq -r '.Battery_recharge_voltage // empty')
    [ ! -z "$Battery_recharge_voltage" ] && pushMQTTData "Battery_recharge_voltage" "$Battery_recharge_voltage"

    Battery_under_voltage=$(echo "$INVERTER_DATA" | jq -r '.Battery_under_voltage // empty')
    [ ! -z "$Battery_under_voltage" ] && pushMQTTData "Battery_under_voltage" "$Battery_under_voltage"

    Battery_bulk_voltage=$(echo "$INVERTER_DATA" | jq -r '.Battery_bulk_voltage // empty')
    [ ! -z "$Battery_bulk_voltage" ] && pushMQTTData "Battery_bulk_voltage" "$Battery_bulk_voltage"

    Battery_float_voltage=$(echo "$INVERTER_DATA" | jq -r '.Battery_float_voltage // empty')
    [ ! -z "$Battery_float_voltage" ] && pushMQTTData "Battery_float_voltage" "$Battery_float_voltage"

    Max_grid_charge_current=$(echo "$INVERTER_DATA" | jq -r '.Max_grid_charge_current // empty')
    [ ! -z "$Max_grid_charge_current" ] && pushMQTTData "Max_grid_charge_current" "$Max_grid_charge_current"

    Max_charge_current=$(echo "$INVERTER_DATA" | jq -r '.Max_charge_current // empty')
    [ ! -z "$Max_charge_current" ] && pushMQTTData "Max_charge_current" "$Max_charge_current"

    Out_source_priority=$(echo "$INVERTER_DATA" | jq -r '.Out_source_priority // empty')
    [ ! -z "$Out_source_priority" ] && pushMQTTData "Out_source_priority" "$Out_source_priority"

    Charger_source_priority=$(echo "$INVERTER_DATA" | jq -r '.Charger_source_priority // empty')
    [ ! -z "$Charger_source_priority" ] && pushMQTTData "Charger_source_priority" "$Charger_source_priority"

    Battery_redischarge_voltage=$(echo "$INVERTER_DATA" | jq -r '.Battery_redischarge_voltage // empty')
    [ ! -z "$Battery_redischarge_voltage" ] && pushMQTTData "Battery_redischarge_voltage" "$Battery_redischarge_voltage"

    Warnings=$(echo "$INVERTER_DATA" | jq -r '.Warnings // empty')
    [ ! -z "$Warnings" ] && pushMQTTData "Warnings" "$Warnings"
}

# === Основной цикл ===
bashio::log.info "Запуск entrypoint.sh для Voltronic..."

# Инициализация MQTT-сенсоров (один раз)
mqtt_init

# Основной цикл: опрос каждые 10 секунд
while true; do
    mqtt_push
    sleep 10
done
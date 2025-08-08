#!/usr/bin/with-contenv bashio

# Получаем параметры из аргументов
MQTT_SERVER=$1
MQTT_PORT=$2
MQTT_TOPIC=$3
MQTT_DEVICENAME=$4
MQTT_USERNAME=$5
MQTT_PASSWORD=$6

pushMQTTData() {
    local name=$1
    local value=$2
    
    # Публикуем только если значение не пустое
    if [ -n "$value" ] && [ "$value" != "null" ]; then
        mosquitto_pub \
            -h "${MQTT_SERVER}" \
            -p "${MQTT_PORT}" \
            -u "${MQTT_USERNAME}" \
            -P "${MQTT_PASSWORD}" \
            -t "${MQTT_TOPIC}/sensor/${MQTT_DEVICENAME}_${name}" \
            -m "${value}" || bashio::log.warning "Failed to publish: ${name}"
    fi
}

# Получаем данные с инвертера
INVERTER_DATA=$(timeout 10 /opt/inverter-cli/bin/inverter_poller -1)

# Логируем полученные данные
TIME=$(date +"%Y-%m-%d %H:%M:%S")
bashio::log.debug "[${TIME}] Inverter data: ${INVERTER_DATA}"

# Парсим и публикуем данные
pushMQTTData "Inverter_mode" "$(echo "${INVERTER_DATA}" | jq -r '.Inverter_mode')"
pushMQTTData "AC_grid_voltage" "$(echo "${INVERTER_DATA}" | jq -r '.AC_grid_voltage')"
pushMQTTData "AC_grid_frequency" "$(echo "${INVERTER_DATA}" | jq -r '.AC_grid_frequency')"
pushMQTTData "AC_out_voltage" "$(echo "${INVERTER_DATA}" | jq -r '.AC_out_voltage')"
pushMQTTData "AC_out_frequency" "$(echo "${INVERTER_DATA}" | jq -r '.AC_out_frequency')"
pushMQTTData "PV_in_voltage" "$(echo "${INVERTER_DATA}" | jq -r '.PV_in_voltage')"
pushMQTTData "PV_in_current" "$(echo "${INVERTER_DATA}" | jq -r '.PV_in_current')"
pushMQTTData "PV_in_watts" "$(echo "${INVERTER_DATA}" | jq -r '.PV_in_watts')"
pushMQTTData "PV_in_watthour" "$(echo "${INVERTER_DATA}" | jq -r '.PV_in_watthour')"
pushMQTTData "SCC_voltage" "$(echo "${INVERTER_DATA}" | jq -r '.SCC_voltage')"
pushMQTTData "Load_pct" "$(echo "${INVERTER_DATA}" | jq -r '.Load_pct')"
pushMQTTData "Load_watt" "$(echo "${INVERTER_DATA}" | jq -r '.Load_watt')"
pushMQTTData "Load_watthour" "$(echo "${INVERTER_DATA}" | jq -r '.Load_watthour')"
pushMQTTData "Load_va" "$(echo "${INVERTER_DATA}" | jq -r '.Load_va')"
pushMQTTData "Bus_voltage" "$(echo "${INVERTER_DATA}" | jq -r '.Bus_voltage')"
pushMQTTData "Heatsink_temperature" "$(echo "${INVERTER_DATA}" | jq -r '.Heatsink_temperature')"
pushMQTTData "Battery_capacity" "$(echo "${INVERTER_DATA}" | jq -r '.Battery_capacity')"
pushMQTTData "Battery_voltage" "$(echo "${INVERTER_DATA}" | jq -r '.Battery_voltage')"
pushMQTTData "Battery_charge_current" "$(echo "${INVERTER_DATA}" | jq -r '.Battery_charge_current')"
pushMQTTData "Battery_discharge_current" "$(echo "${INVERTER_DATA}" | jq -r '.Battery_discharge_current')"
pushMQTTData "Load_status_on" "$(echo "${INVERTER_DATA}" | jq -r '.Load_status_on')"
pushMQTTData "SCC_charge_on" "$(echo "${INVERTER_DATA}" | jq -r '.SCC_charge_on')"
pushMQTTData "AC_charge_on" "$(echo "${INVERTER_DATA}" | jq -r '.AC_charge_on')"
pushMQTTData "Battery_recharge_voltage" "$(echo "${INVERTER_DATA}" | jq -r '.Battery_recharge_voltage')"
pushMQTTData "Battery_under_voltage" "$(echo "${INVERTER_DATA}" | jq -r '.Battery_under_voltage')"
pushMQTTData "Battery_bulk_voltage" "$(echo "${INVERTER_DATA}" | jq -r '.Battery_bulk_voltage')"
pushMQTTData "Battery_float_voltage" "$(echo "${INVERTER_DATA}" | jq -r '.Battery_float_voltage')"
pushMQTTData "Max_grid_charge_current" "$(echo "${INVERTER_DATA}" | jq -r '.Max_grid_charge_current')"
pushMQTTData "Max_charge_current" "$(echo "${INVERTER_DATA}" | jq -r '.Max_charge_current')"
pushMQTTData "Out_source_priority" "$(echo "${INVERTER_DATA}" | jq -r '.Out_source_priority')"
pushMQTTData "Charger_source_priority" "$(echo "${INVERTER_DATA}" | jq -r '.Charger_source_priority')"
pushMQTTData "Battery_redischarge_voltage" "$(echo "${INVERTER_DATA}" | jq -r '.Battery_redischarge_voltage')"
pushMQTTData "Warnings" "$(echo "${INVERTER_DATA}" | jq -r '.Warnings')"

bashio::log.info "Data published to MQTT"
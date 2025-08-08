#!/usr/bin/with-contenv bashio

# Получаем параметры из аргументов
MQTT_SERVER=$1
MQTT_PORT=$2
MQTT_TOPIC=$3
MQTT_DEVICENAME=$4
MQTT_USERNAME=$5
MQTT_PASSWORD=$6

registerTopic() {
    local name=$1
    local unit=$2
    local icon=$3
    
    mosquitto_pub \
        -h "${MQTT_SERVER}" \
        -p "${MQTT_PORT}" \
        -u "${MQTT_USERNAME}" \
        -P "${MQTT_PASSWORD}" \
        -t "${MQTT_TOPIC}/sensor/${MQTT_DEVICENAME}_${name}/config" \
        -m "{
            \"name\": \"${MQTT_DEVICENAME}_${name}\",
            \"unit_of_measurement\": \"${unit}\",
            \"state_topic\": \"${MQTT_TOPIC}/sensor/${MQTT_DEVICENAME}_${name}\",
            \"icon\": \"mdi:${icon}\"
        }" || bashio::log.error "Failed to register topic: ${name}"
}

registerInverterRawCMD() {
    mosquitto_pub \
        -h "${MQTT_SERVER}" \
        -p "${MQTT_PORT}" \
        -u "${MQTT_USERNAME}" \
        -P "${MQTT_PASSWORD}" \
        -t "${MQTT_TOPIC}/sensor/${MQTT_DEVICENAME}/config" \
        -m "{
            \"name\": \"${MQTT_DEVICENAME}\",
            \"state_topic\": \"${MQTT_TOPIC}/sensor/${MQTT_DEVICENAME}\"
        }" || bashio::log.error "Failed to register raw command topic"
}

# Регистрация всех топиков
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
registerTopic "Heatsink_temperature" "°C" "thermometer"
registerTopic "Battery_capacity" "%" "battery"
registerTopic "Battery_voltage" "V" "battery"
registerTopic "Battery_charge_current" "A" "current-dc"
registerTopic "Battery_discharge_current" "A" "current-dc"
registerTopic "Load_status_on" "" "power"
registerTopic "SCC_charge_on" "" "power"
registerTopic "AC_charge_on" "" "power"
registerTopic "Battery_recharge_voltage" "V" "current-dc"
registerTopic "Battery_under_voltage" "V" "current-dc"
registerTopic "Battery_bulk_voltage" "V" "current-dc"
registerTopic "Battery_float_voltage" "V" "current-dc"
registerTopic "Max_grid_charge_current" "A" "current-ac"
registerTopic "Max_charge_current" "A" "current-ac"
registerTopic "Out_source_priority" "" "grid"
registerTopic "Charger_source_priority" "" "solar-power"
registerTopic "Battery_redischarge_voltage" "V" "battery-negative"

# Регистрация топика для raw-команд
registerInverterRawCMD

bashio::log.info "MQTT topics registered successfully"
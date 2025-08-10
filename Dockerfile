ARG BUILD_FROM
FROM ${BUILD_FROM} AS build

RUN apk add --no-cache build-base cmake libstdc++-dev
ADD src/inverter-cli /src/inverter-cli
RUN cd /src/inverter-cli \
   && cmake -Bbuild -H. -DCMAKE_INSTALL_PREFIX=/opt/inverter-cli \
    && cmake --build build \
    && cmake --install build

FROM $BUILD_FROM AS final

# Build arguments
ARG BUILD_ARCH
ARG BUILD_DATE
ARG BUILD_DESCRIPTION
ARG BUILD_NAME
ARG BUILD_REF
ARG BUILD_REPOSITORY
ARG BUILD_VERSION

# Labels
LABEL \
    io.hass.name="${BUILD_NAME}" \
    io.hass.description="${BUILD_DESCRIPTION}" \
    io.hass.arch="${BUILD_ARCH}" \
    io.hass.type="addon" \
    io.hass.version=${BUILD_VERSION} \
    maintainer="D.Kadyshev" \
    org.opencontainers.image.title="${BUILD_NAME}" \
    org.opencontainers.image.description="${BUILD_DESCRIPTION}" \
    org.opencontainers.image.vendor="Home Assistant Community Add-ons" \
    org.opencontainers.image.authors="D.Kadyshev" \
    org.opencontainers.image.licenses="MIT" \
    org.opencontainers.image.url="https://addons.community" \
    org.opencontainers.image.source="https://github.com/${BUILD_REPOSITORY}" \
    org.opencontainers.image.documentation="https://github.com/${BUILD_REPOSITORY}/blob/main/README.md" \
    org.opencontainers.image.created=${BUILD_DATE} \
    org.opencontainers.image.revision=${BUILD_REF} \
    org.opencontainers.image.version=${BUILD_VERSION}

# Установка зависимостей
RUN apk add --no-cache bash mosquitto-clients jq

# Копируем s6-службы
COPY src/rootfs/ /

# Копируем скрипты
COPY src/mqtt-init.sh /opt/inverter-mqtt/
COPY src/mqtt-push.sh /opt/inverter-mqtt/
RUN chmod +x /opt/inverter-mqtt/*.sh && mkdir -p /etc/inverter/ 

# Копируем бинарник inverter-cli
COPY --from=build /opt/inverter-cli/bin /opt/inverter-cli/bin

# Устанавливаем права на скрипты s6
RUN chmod +x /etc/services.d/inverter/run && \
    chmod +x /etc/services.d/inverter/finish

# Точка входа s6-overlay
ENTRYPOINT ["/init"]
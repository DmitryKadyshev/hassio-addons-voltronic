ARG BUILD_FROM
FROM $BUILD_FROM AS build

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ENV XDG_CONFIG_HOME="/config"

RUN apk add --no-cache build-base cmake  libstdc++-dev
ADD src/inverter-cli /src/inverter-cli
RUN cd /src/inverter-cli \
   && cmake -Bbuild -H. -DCMAKE_INSTALL_PREFIX=/opt/inverter-cli \
    && cmake --build build \
    && cmake --install build

FROM $BUILD_FROM AS final
ENV LANG=C.UTF-8
RUN apk add --no-cache bash mosquitto-clients jq
WORKDIR /opt/inverter-cli
COPY src/entrypoint.sh /
RUN chmod +x /entrypoint.sh
COPY --from=build /opt/inverter-cli/bin /opt/inverter-cli
CMD ["/entrypoint.sh"]

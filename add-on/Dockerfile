ARG BUILD_FROM
FROM $BUILD_FROM

# system deps + uv from apk
RUN apk add --no-cache \
  python3 uv git
WORKDIR /app

# clone service
RUN git clone https://github.com/nycresistor/Hexascroller.git /app/Hexascroller

# create venv and add to PATH
RUN uv venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

# install deps & package
WORKDIR /app/Hexascroller/hexaservice
RUN uv sync --no-interaction

# copy entrypoint
COPY run.sh /app/run.sh
RUN chmod a+x /app/run.sh

CMD [ "/app/run.sh" ]

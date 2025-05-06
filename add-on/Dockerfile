ARG BUILD_FROM
FROM $BUILD_FROM

# system deps + uv from apk
RUN apk add --no-cache git python3 uv
WORKDIR /app

# clone service and create venv
RUN git clone https://github.com/nycresistor/Hexascroller.git /app/Hexascroller \
&& uv venv /app/venv

# install deps & package
WORKDIR /app/Hexascroller/hexaservice
RUN uv pip install -r requirements.txt

# copy entrypoint
COPY run.sh /app/run.sh
RUN chmod a+x /app/run.sh

CMD [ "/app/run.sh" ]

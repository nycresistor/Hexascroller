ARG BUILD_FROM
FROM $BUILD_FROM

# Install requirements for add-on
RUN \
  apk add --no-cache \
    python3 git py3-pip

WORKDIR /app
# Clone the hexaservice files from the git repository
RUN git clone https://github.com/nycresistor/Hexascroller.git /app/Hexascroller
RUN pip install --no-cache-dir -r /app/Hexascroller/hexaservice/requirements.txt

# Copy data for add-on
COPY run.sh /app
RUN chmod a+x /app/run.sh
CMD [ "/app/run.sh" ]
FROM alpine:latest

RUN apk add --update --no-cache python3 py3-pip gcc g++ python3-dev musl-dev
RUN pip3 install --no-cache --upgrade pip setuptools minimalmodbus influxdb influxdb-client[ciso] --break-system-packages

RUN mkdir /monitor
WORKDIR /monitor
COPY monitor.py /monitor
COPY ups /monitor/ups

RUN echo "* * * * * python3 /monitor/monitor.py" >> /etc/crontabs/root && crontab -l
CMD crond -f -l 8

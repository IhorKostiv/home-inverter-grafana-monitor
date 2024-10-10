FROM alpine:latest

RUN apk add --update --no-cache python3 py3-pip gcc g++ python3-dev musl-dev
RUN pip3 install --no-cache --upgrade pip setuptools datetime influxdb influxdb-client[ciso] --break-system-packages

RUN mkdir /forecast.solar
WORKDIR /forecast.solar
COPY forecastsolar.py /forecast.solar

RUN echo "6,21,36,51 * * * * python3 /forecast.solar/forecastsolar.py" >> /etc/crontabs/root && crontab -l
CMD crond -f -l 8

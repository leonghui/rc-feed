FROM python:alpine

RUN addgroup -g 1001 app \
    && adduser -u 1001 -S -D -G app -s /usr/sbin/nologin app

# use GNU wget to handle SSL properly
RUN apk update && apk upgrade && \
    apk add --no-cache tzdata firefox wget

# download and install latest Geckodriver
# credits to https://github.com/prantlf/docker-geckodriver-headless/blob/master/Dockerfile
RUN cd /root && \
    BASE_URL=https://github.com/mozilla/geckodriver/releases/download && \
    VERSION=$(wget -O- https://api.github.com/repos/mozilla/geckodriver/releases/latest | \
      grep tag_name | cut -d '"' -f 4) && \
    wget "$BASE_URL/$VERSION/geckodriver-$VERSION-linux64.tar.gz" && \
    tar xf geckodriver-$VERSION-linux64.tar.gz geckodriver -C /usr/local/bin && \
    rm geckodriver-$VERSION-linux64.tar.gz

COPY . /app/
WORKDIR /app/
RUN pip install -r requirements.txt

USER app

EXPOSE 5000
ENTRYPOINT ["python"]
CMD ["server.py"]

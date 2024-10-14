FROM python:3.9-slim-bullseye AS basetelethon

RUN \
	sed -i -e's/ main/ main contrib non-free/g' /etc/apt/sources.list \
	&& apt-get -q update \
	&& apt-get -qy dist-upgrade

RUN \
	apt-get install -qy ffmpeg \
	rustc \
	gcc libffi-dev libssl-dev python3-dev \
	unzip \
	unrar \
	#python3 \
	#python3-setuptools \
	python3-pip && \
	#usermod -d /app abc  && \
	apt-get remove --purge -y build-essential  && \
	apt-get autoclean -y && apt-get autoremove -y  && \
	rm -rf /default /etc/default /tmp/* /etc/cont-init.d/* /var/lib/apt/lists/* /var/tmp/*

WORKDIR /app

COPY requirements.txt requirements.txt

RUN \
	python3 -m pip install --upgrade pip  && \
	pip3 install -r requirements.txt --upgrade  --root-user-action=ignore

COPY 7zz /usr/local/bin/7zz
RUN chmod 777 /usr/local/bin/7zz

FROM basetelethon

COPY telethon-downloader /app
COPY root/ /

RUN chmod 777 /app/bottorrent.py
RUN chmod 777 -R /etc/services.d/


VOLUME /download /watch /config

CMD ["python3", "/app/bottorrent.py"]

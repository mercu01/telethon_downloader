FROM python:3 AS basetelethon


WORKDIR /app

COPY requirements.txt requirements.txt


RUN	sed -i -e's/ main/ main contrib non-free/g' /etc/apt/sources.list \
	&& apt-get -q update                                              \
	&& apt-get -qy dist-upgrade                                       \
	&& apt-get update && apt-get upgrade -y  \ 
	&& apt-get install -y \
	ffmpeg \
	unrar \
	#python3 \
	#python3-setuptools \
	python3-pip && \
	#usermod -d /app abc  && \
	python3 -m pip install --upgrade pip  && \
	pip3 install -r requirements.txt --upgrade && \
	apt-get remove --purge -y build-essential  && \
	apt-get autoclean -y && apt-get autoremove -y  && \
	rm -rf /default /etc/default /tmp/* /etc/cont-init.d/* /var/lib/apt/lists/* /var/tmp/*



FROM basetelethon

COPY telethon-downloader /app
COPY root/ /

RUN chmod 777 /app/bottorrent.py
RUN chmod 777 -R /etc/services.d/


VOLUME /download /watch /config

CMD ["python3", "/app/bottorrent.py"]

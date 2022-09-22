FROM python:3.10.5-bullseye

RUN apt update && apt install -y ffmpeg

RUN pip3 install click python-dotenv discord.py[voice] youtube_dl d20

WORKDIR /tobybot

COPY ./ .

COPY images/ images/

CMD ["python3", "-u", "discordbot.py"]
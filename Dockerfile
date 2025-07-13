FROM python:3.10

WORKDIR /app

RUN apt-get update && \
    apt-get install -y build-essential wget unzip swig

COPY requirements.txt requirements.txt
RUN pip3 install --upgrade pip && pip3 install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /usr/share/swisseph /usr/local/share/swisseph
COPY ephe/seas_18.se1 /usr/share/swisseph/seas_18.se1
COPY ephe/sepl_18.se1 /usr/share/swisseph/sepl_18.se1
COPY ephe/seas_18.se1 /usr/local/share/swisseph/seas_18.se1
COPY ephe/sepl_18.se1 /usr/local/share/swisseph/sepl_18.se1

# ENV ile path'i kesinlikle bildir
ENV SWEPHEPATH="/usr/share/swisseph:/usr/local/share/swisseph"


RUN ls -lh /usr/share/swisseph && ls -lh /usr/local/share/swisseph

CMD ["gunicorn", "-b", "0.0.0.0:8000", "app:app"]

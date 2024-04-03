FROM python:3.11-slim

ARG PACKAGE_NAME=package
ARG DIR_NAME=ocr_rag
ARG USER=user
ARG WORKDIR=/app

WORKDIR $WORKDIR

RUN apt-get update \
    && apt-get install -y --no-install-recommends apt-utils \
    vim curl wget git fish \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir --upgrade pip setuptools
COPY ./requirements.txt $WORKDIR/requirements.txt
COPY ./setup.py $WORKDIR/setup.py
RUN pip3 install --no-cache-dir -r $WORKDIR/requirements.txt
COPY --chown=${USER}:${USER} ./$DIR_NAME/ $WORKDIR/$DIR_NAME/
RUN pip3 install -e $WORKDIR/$DIR_NAME/

COPY ./test.py $WORKDIR/test.py
COPY ./pytest.ini $WORKDIR/pytest.ini

RUN useradd --create-home ${USER}
RUN chown -R ${USER}:${USER} $WORKDIR

USER ${USER}

EXPOSE 8000

CMD ["sh", "-c", "cd /app/$DIR_NAME/ && uvicorn main:app --host 0.0.0.0 --port 8000"]

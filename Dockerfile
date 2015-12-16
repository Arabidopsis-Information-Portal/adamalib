FROM jupyter/scipy-notebook

COPY . /adamalib
WORKDIR /adamalib
USER root
RUN apt-get update
RUN apt-get install -y libxml2-dev libxslt1-dev python-dev libffi-dev libssl-dev
RUN /opt/conda/envs/python2/bin/pip install -U pip
RUN /opt/conda/envs/python2/bin/pip install requests[security]
RUN /opt/conda/envs/python2/bin/pip install six
RUN /opt/conda/envs/python2/bin/pip install -r requirements.txt
RUN /opt/conda/envs/python2/bin/python setup.py develop

COPY notebooks/ /data
RUN git init /data/provn
WORKDIR /data

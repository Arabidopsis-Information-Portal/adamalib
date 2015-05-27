FROM ipython/notebook

COPY . /adamalib
WORKDIR /adamalib
RUN apt-get update
RUN apt-get install -y libxml2-dev libxslt1-dev python-dev libffi-dev
RUN pip install -U pip
RUN pip install -U requests[security]
RUN pip uninstall -y six
RUN pip install six
RUN pip install -r requirements.txt
RUN python setup.py develop

COPY notebooks/ /data
RUN git init /data/provn
WORKDIR /data

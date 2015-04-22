FROM ipython/notebook

COPY . /adamalib
WORKDIR /adamalib
RUN pip install -r requirements.txt
RUN python setup.py install

COPY notebooks /notebooks
WORKDIR /notebooks

FROM ubuntu:20.04

ENV DIRPATH /sw
WORKDIR $DIRPATH
ENV NETWORK_CACHE /sw/indra_network_search/indra_network_search/_cache

RUN apt-get update && \
    DEBIAN_FRONTEND="noninteractive" apt-get -y install tzdata && \
    apt-get install -y git wget gcc pkg-config python3 python3-pip \
        graphviz graphviz-dev libpq-dev && \
    ln -s /usr/bin/python3 /usr/bin/python

RUN git clone https://github.com/indralab/indra_network_search.git && \
    cd indra_network_search && \
    pip install . && \
    cd .. && \
    mkdir -p $NETWORK_CACHE && \
    pip install gunicorn uvicorn termcolor cachetools 'SQLAlchemy<1.4' && \
    git clone https://github.com/indralab/depmap_analysis.git && \
    python -m indra.ontology.bio build

ADD indranet_dir_graph.pkl $NETWORK_CACHE
ADD indranet_sign_node_graph.pkl $NETWORK_CACHE

ENV PYTHONPATH /sw/depmap_analysis:/sw/indra_network_search
ENV USE_CACHE 1
ENV DUMPS_BUCKET "gyori-bigmech"
ENV CACHE_RESULTS 1

ENTRYPOINT ["gunicorn", "-w", "1", "-b", "0.0.0.0:8000", "-t", "600", "-k", "uvicorn.workers.UvicornWorker", "indra_network_search.rest_api:app"]

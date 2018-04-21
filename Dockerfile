FROM ubuntu:rolling AS deps
WORKDIR /tmp
ENV LANG='en_US.UTF-8' LC_ALL='en_US.UTF-8'

# install dependencies
RUN apt-get update -qq && \
    apt-get install -y locales && locale-gen en_US.UTF-8 && \
    apt-get install -y python3 python3-pip firefox xvfb ca-certificates bash wget && \
    pip3 --no-cache-dir install 'pipenv~=11.0'

# install geckodriver
RUN wget -qO /tmp/geckodriver.tar.gz https://github.com/mozilla/geckodriver/releases/download/v0.20.1/geckodriver-v0.20.1-linux64.tar.gz && \
    tar xf /tmp/geckodriver.tar.gz -C /tmp && mv /tmp/geckodriver /usr/bin/geckodriver && chmod +x /usr/bin/geckodriver


# install pipenv dependencies
COPY Pipfile.lock Pipfile ./
RUN pipenv --site-packages --three install --system --deploy && pip3 --no-cache-dir uninstall -y pipenv

# cleanup
RUN apt-get autoremove -y && apt-get clean && apt-get autoclean && rm -rfv /var/lib/apt /var/cache /tmp

FROM ubuntu:rolling
ENV LANG='en_US.UTF-8' LC_ALL='en_US.UTF-8'
COPY --from=deps / /

# configure user and workdir
RUN useradd -rUm -u 1000 user && mkdir -p /workdir && chown -R user:user /workdir
USER user
WORKDIR /workdir

ADD cache-preload.py /opt/cache-preload.py
ENTRYPOINT ["/usr/bin/python3", "-O", "/opt/cache-preload.py"]
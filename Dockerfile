FROM mono:5 as buildenv

ARG APSIM_TAG="Apsim710"
RUN apt-get update 
RUN DEBIAN_FRONTEND=noninteractive apt-get -y install apt-utils g++ gfortran libxml2-dev tcl8.5 tcl8.5-dev tcllib subversion p7zip p7zip-full

#install mono and R
RUN DEBIAN_FRONTEND=noninteractive apt-get -y install \
	r-base \
	r-base-dev \
	r-recommended 

RUN Rscript -e 'install.packages(c("Rcpp", "RInside", "inline"),repos = "https://cran.cnr.berkeley.edu")'

RUN svn co https://apsrunet.apsim.info/svn/apsim/tags/${APSIM_TAG} apsim 

RUN echo CsiroDMZ\! > /etc/CottonPassword.txt
ENV APSIM /apsim

RUN cd /apsim/Model/Build && \
  chmod +x BuildAll.sh && \
  ./BuildAll.sh && \
  export APSIM=/apsim && \
  cd /apsim/Release && \
  ./Release.sh

RUN rm -f /etc/CottonPassword.txt

FROM mono:5

#install mono, R and python3 (and less for debugging)
RUN apt-get update
RUN DEBIAN_FRONTEND=noninteractive apt-get -y install libxml2 tcl8.5 r-recommended python3 python3-pip python3-bs4 less \
    && rm -rf /var/lib/apt/lists/* 
RUN Rscript -e 'install.packages(c("Rcpp", "RInside", "inline"),repos = "https://cran.cnr.berkeley.edu")'


# copy extract binary bundle 
COPY --from=buildenv /apsim/Release/Apsim*.binaries.LINUX.X86_64.exe /tmp/apsim-release.exe
RUN ls -al --block-size=M /tmp/apsim-release.exe
RUN /tmp/apsim-release.exe -y -o/apsim 
RUN rm -f /tmp/apsim-release.exe 
RUN chmod 755 apsim

# storage folder to mount NFS filesystem
ENV WORK_FOLDER /storage
RUN mkdir ${WORK_FOLDER}
RUN chmod -R 777 ${WORK_FOLDER}

WORKDIR /apsim/Temp/Model
ENV LD_LIBRARY_PATH=/apsim/Temp/Model

RUN ln -s /usr/bin/python3 /bin/python
RUN ln -s /usr/bin/pip3 /bin/pip

RUN pip install zmq

RUN mkdir -p /apsim_proxy/run
COPY ./apsim_zmq_wrapper_linux.py /apsim_proxy/run

CMD ["python", "/apsim_proxy/run/apsim_zmq_wrapper_linux.py"]
EXPOSE 5551 5552